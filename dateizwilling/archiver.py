"""Archivieren, Wiederherstellen nach Absturz, Rueckgaengig, Loeschen nach Freigabe.

Sicherheitsprinzipien
---------------------
* Es wird NIE etwas geloescht, ohne dass zuvor eine verifizierte Kopie im
  Archiv liegt (gleicher Laufwerk: atomares Umbenennen; anderes Laufwerk:
  Kopie -> fsync -> Ruecklesen + Pruefsumme -> erst dann Quelle entfernen).
* Vor jedem Verschieben wird das Duplikat erneut gegen das behaltene Original
  geprueft (Byte fuer Byte oder Pruefsumme). Fehlt das Original oder weicht
  der Inhalt ab, wird die Datei NICHT angefasst.
* Ziel-Dateien werden nie ueberschrieben.
* Jeder Schritt steht vorher im Journal (Write-Ahead). Nach einem Absturz
  wird jeder halbfertige Schritt erkannt und sauber beendet oder
  zurueckgerollt; danach laeuft der Auftrag an derselben Stelle weiter.
* Endgueltiges Entfernen erst nach ausdruecklicher Freigabe – und nur, wenn
  das behaltene Original zu diesem Zeitpunkt noch vorhanden ist.
"""
from __future__ import annotations

import csv
import errno
import logging
import os
import shutil
import time

from .common import (CHUNK, Cancelled, Control, ProgressFn, RateMeter, csv_safe, files_equal,
                     hash_full)
from . import formats
from .pathutil import (archive_target, fs, is_within, norm_key, send_to_trash, unfs,
                       unique_path)
from .state import (J_COPIED, J_COPYING, J_DONE, J_FAILED, J_PLANNED, J_PURGED, J_SKIPPED,
                    J_UNDONE, OPEN_STATES, Store)

log = logging.getLogger("dateizwilling.archive")

MANIFEST_DIR = "_DateiZwilling"


class CrossDevice(Exception):
    pass


def _is_cross_device(exc: OSError) -> bool:
    return exc.errno == errno.EXDEV or getattr(exc, "winerror", None) == 17


def _fsync_dir(folder: str) -> None:
    if os.name == "nt":
        return
    try:
        fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _remove_file(path: str) -> None:
    try:
        os.remove(fs(path))
    except PermissionError:
        # schreibgeschuetzte Datei (Windows): Schutz aufheben und erneut versuchen
        os.chmod(fs(path), 0o666)
        os.remove(fs(path))


def _remove_empty_dirs(start: str, stop: str) -> None:
    """Entfernt leere Ordner von *start* aufwaerts bis (ausschliesslich) *stop*."""
    cur = os.path.abspath(start)
    stop = os.path.abspath(stop)
    while is_within(cur, stop) and norm_key(cur) != norm_key(stop):
        try:
            os.rmdir(fs(cur))
        except OSError:
            return
        cur = os.path.dirname(cur)


class Archiver:
    def __init__(self, store: Store, control: Control, progress: ProgressFn | None = None,
                 verify_bytes: bool = True):
        self.store = store
        self.control = control
        self.progress = progress or (lambda d: None)
        self.verify_bytes = verify_bytes
        self._bytes = 0
        self._meter = RateMeter()
        self._last_emit = 0.0
        self._ctx: dict = {}

    # ---------------------------------------------------------------- Hilfen
    def _emit(self, force: bool = False, **kw) -> None:
        now = time.monotonic()
        if not force and now - self._last_emit < 0.25:
            return
        self._last_emit = now
        self._meter.update(self._bytes)
        for k, v in self._ctx.items():
            kw.setdefault(k, v)
        kw.setdefault("bytes", self._bytes)
        kw["rate"] = self._meter.rate()
        try:
            self.progress(kw)
        except Exception:
            log.exception("Fortschrittsrueckmeldung fehlgeschlagen")

    def _add_bytes(self, n: int) -> None:
        self._bytes += n

    def _manifest_path(self, archive: str, run_id: int, kind: str) -> str:
        folder = os.path.join(archive, MANIFEST_DIR)
        os.makedirs(fs(folder), exist_ok=True)
        name = {"archive": "Archivierung", "undo": "Rueckgaengig", "purge": "Bereinigung"}.get(kind, kind)
        return os.path.join(folder, f"{name}-Lauf-{run_id:05d}.csv")

    def _manifest_row(self, path: str, row: list) -> None:
        new = not os.path.exists(fs(path))
        try:
            with open(fs(path), "a", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh, delimiter=";")
                if new:
                    w.writerow(["Zeitpunkt", "Status", "Originalpfad", "Archivpfad",
                                "Behaltenes Original", "Groesse (Bytes)", "BLAKE2b-256",
                                "Begleitdatei"])
                w.writerow([csv_safe(x) for x in row])
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as exc:
            log.warning("Manifest konnte nicht geschrieben werden (%s): %s", path, exc)

    # ---------------------------------------------------------------- Kernoperation
    def _copy_verified(self, src: str, tmp: str) -> str:
        """Kopiert src -> tmp, fsync, liest tmp zurueck und vergleicht die
        Pruefsumme. Rueckgabe: Pruefsumme. Bei Abweichung Exception."""
        import hashlib
        h_src = hashlib.blake2b(digest_size=32)
        n = 0
        with open(fs(src), "rb") as fi, open(fs(tmp), "xb") as fo:
            while True:
                buf = fi.read(CHUNK)
                if not buf:
                    break
                h_src.update(buf)
                fo.write(buf)
                self._add_bytes(len(buf))
                n += 1
                if n % 8 == 0:
                    self.control.checkpoint()
                    self._emit(current=src)
            fo.flush()
            os.fsync(fo.fileno())
        src_hash = h_src.hexdigest()
        back = hash_full(tmp, self.control)
        if back != src_hash:
            raise OSError(f"Verifikation der Kopie fehlgeschlagen ({tmp})")
        try:
            shutil.copystat(fs(src), fs(tmp), follow_symlinks=False)
        except OSError:
            pass
        return src_hash

    def _move(self, jid: int, src: str, dst: str, expected_hash: str | None) -> str | None:
        """Verschiebt sicher. Rueckgabe: Pruefsumme (falls berechnet)."""
        parent = os.path.dirname(dst)
        os.makedirs(fs(parent), exist_ok=True)
        if os.path.lexists(fs(dst)):
            raise FileExistsError(dst)
        try:
            os.rename(fs(src), fs(dst))  # gleiches Laufwerk: atomar
            _fsync_dir(parent)
            try:
                self._add_bytes(os.path.getsize(fs(dst)))
            except OSError:
                pass
            return None
        except OSError as exc:
            if not _is_cross_device(exc):
                raise
        # anderes Laufwerk: Kopie mit Verifikation
        tmp = dst + ".dzpart"
        if os.path.lexists(fs(tmp)):
            _remove_file(tmp)
        self.store.journal_set(jid, J_COPYING, tmp=tmp)
        try:
            h = self._copy_verified(src, tmp)
            if expected_hash and h != expected_hash:
                raise OSError("Inhalt entspricht nicht mehr der gescannten Pruefsumme")
            if os.path.lexists(fs(dst)):
                raise FileExistsError(dst)
            os.rename(fs(tmp), fs(dst))
            _fsync_dir(parent)
        except BaseException:
            try:
                if os.path.lexists(fs(tmp)):
                    _remove_file(tmp)
            except OSError:
                pass
            raise
        self.store.journal_set(jid, J_COPIED, h=h)
        try:
            _remove_file(src)
        except OSError as exc:
            # Quelle laesst sich nicht entfernen -> Ziel wieder entfernen,
            # damit kein halber Zustand bleibt
            try:
                _remove_file(dst)
            except OSError:
                pass
            raise OSError(f"Quelle konnte nicht entfernt werden: {exc}") from exc
        return h

    # ---------------------------------------------------------------- Planung
    def plan_archive(self, session_id: int, groups: list[dict], archive: str,
                     move_sidecars: bool = True) -> int:
        """Legt einen Archivierungs-Lauf an und schreibt den kompletten Plan
        ins Journal. Rueckgabe: Lauf-Nummer."""
        archive = os.path.abspath(unfs(archive))
        os.makedirs(fs(archive), exist_ok=True)
        run_id = self.store.run_create(session_id, "archive", archive)
        rows: list[dict] = []
        taken: set[str] = set()
        moving_keys: set[str] = set()
        for g in groups:
            for m in g["members"]:
                if not m.get("keep") and m.get("state", "open") == "open":
                    moving_keys.add(norm_key(m["path"]))
        for g in groups:
            keepers = [m["path"] for m in g["members"] if m.get("keep")]
            movers = [m for m in g["members"] if not m.get("keep") and m.get("state", "open") == "open"]
            if not keepers or not movers:
                continue
            for m in movers:
                dst = self._free_target(archive, m["path"], taken)
                rows.append({"src": m["path"], "dst": dst, "size": g["size"], "hash": g["hash"],
                             "keeper": keepers[0], "gid": g["gid"], "session_id": session_id})
                if move_sidecars:
                    for sc in formats.find_sidecars(m["path"]):
                        sk = norm_key(sc)
                        if sk in moving_keys:
                            continue  # ist selbst ein Duplikat – wird ohnehin verschoben
                        if formats.sidecar_stem_shared(sc, m["path"]) and self._stem_sibling_stays(
                                sc, m["path"], moving_keys):
                            continue  # gehoert auch zu einer bleibenden Datei (RAW+JPEG)
                        moving_keys.add(sk)
                        rows.append({"src": sc, "dst": self._free_target(archive, sc, taken),
                                     "size": None, "hash": None, "keeper": m["path"],
                                     "sidecar": True, "gid": g["gid"], "session_id": session_id})
        self.store.journal_plan(run_id, rows)
        log.info("Archivierungs-Lauf %s geplant: %s Eintraege -> %s", run_id, len(rows), archive)
        return run_id

    @staticmethod
    def _free_target(archive: str, src: str, taken: set[str]) -> str:
        dst = archive_target(archive, src)
        cand = unique_path(dst)
        if norm_key(cand) in taken:
            stem, dot, ext = dst.rpartition(".")
            i = 2
            while True:
                cand = f"{stem} (DZ{i}).{ext}" if dot else f"{dst} (DZ{i})"
                if norm_key(cand) not in taken and not os.path.lexists(fs(cand)):
                    break
                i += 1
        taken.add(norm_key(cand))
        return cand

    @staticmethod
    def _stem_sibling_stays(sidecar: str, owner: str, moving: set[str]) -> bool:
        folder = os.path.dirname(owner)
        stem = os.path.basename(sidecar).rsplit(".", 1)[0].lower()
        try:
            for name in os.listdir(fs(folder)):
                full = os.path.join(folder, name)
                if norm_key(full) in (norm_key(owner), norm_key(sidecar)):
                    continue
                if name.lower().rsplit(".", 1)[0] == stem and norm_key(full) not in moving:
                    return True
        except OSError:
            return True  # im Zweifel nicht verschieben
        return False

    def plan_undo(self, archive_run_id: int) -> int:
        """Plant das Zurueckverschieben eines Archivierungs-Laufs."""
        ref = self.store.run_get(archive_run_id)
        if not ref or ref["kind"] != "archive":
            raise ValueError("Kein Archivierungs-Lauf")
        run_id = self.store.run_create(ref["session_id"], "undo", ref["archive"], archive_run_id)
        rows = []
        for e in reversed(self.store.journal_entries(archive_run_id, (J_DONE,))):
            rows.append({"src": e["dst"], "dst": e["src"], "size": e["size"], "hash": e["hash"],
                         "keeper": None, "sidecar": bool(e["sidecar"]), "ref_id": e["id"],
                         "gid": e["gid"], "session_id": e["session_id"]})
        self.store.journal_plan(run_id, rows)
        return run_id

    # ---------------------------------------------------------------- Ausfuehrung
    def execute(self, run_id: int) -> dict:
        """Fuehrt alle offenen Schritte eines Laufs aus (auch nach Absturz)."""
        run = self.store.run_get(run_id)
        if not run:
            raise ValueError(f"Lauf {run_id} unbekannt")
        if not os.path.isdir(fs(run["archive"])):
            raise OSError(f"Archivordner nicht erreichbar: {run['archive']} – "
                          "bitte Laufwerk verbinden, der Lauf bleibt zum Fortsetzen erhalten")
        self.recover_run(run_id)
        manifest = self._manifest_path(run["archive"], run_id, run["kind"])
        entries = self.store.journal_entries(run_id)
        total = len(entries)
        total_bytes = sum(e["size"] or 0 for e in entries)
        state_by_src = {norm_key(e["src"]): e["state"] for e in entries}
        stats = {"done": 0, "skipped": 0, "failed": 0, "bytes": 0}
        for e in entries:
            if e["state"] == J_DONE:
                stats["done"] += 1
            elif e["state"] in (J_SKIPPED, J_FAILED):
                stats[e["state"] if e["state"] == J_FAILED else "skipped"] += 1
        try:
            for idx, e in enumerate(entries, 1):
                if e["state"] != J_PLANNED:
                    continue
                self.control.checkpoint()
                self._ctx = {"phase": run["kind"], "files": idx, "total": total,
                             "total_bytes": total_bytes}
                self._emit(current=e["src"])
                state, msg, h = self._execute_entry(run, e, state_by_src)
                self.store.journal_set(e["id"], state, error=msg, h=h)
                state_by_src[norm_key(e["src"])] = state
                if state == J_DONE:
                    stats["done"] += 1
                    stats["bytes"] += e["size"] or 0
                    self._after_done(run, e, manifest, h)
                elif state == J_FAILED:
                    stats["failed"] += 1
                    log.warning("Fehlgeschlagen: %s – %s", e["src"], msg)
                else:
                    stats["skipped"] += 1
                    log.info("Uebersprungen: %s – %s", e["src"], msg)
        except Cancelled:
            for e in self.store.journal_entries(run_id, (J_PLANNED,)):
                self.store.journal_set(e["id"], J_SKIPPED, error="vom Benutzer abgebrochen")
                stats["skipped"] += 1
            self.store.run_finish(run_id, "cancelled", stats)
            self._emit(force=True, phase=run["kind"], files=total, total=total)
            raise
        self.store.run_finish(run_id, "done", stats)
        if run["kind"] == "undo":
            _remove_empty_dirs_tree(run["archive"])
        self._emit(force=True, phase=run["kind"], files=total, total=total)
        log.info("Lauf %s (%s) beendet: %s", run_id, run["kind"], stats)
        return stats

    def _execute_entry(self, run: dict, e: dict, state_by_src: dict) -> tuple[str, str | None, str | None]:
        src, dst = e["src"], e["dst"]
        try:
            if not os.path.lexists(fs(src)):
                return J_FAILED, "Quelle nicht mehr vorhanden", None
            if os.path.islink(fs(src)):
                return J_SKIPPED, "symbolische Verknuepfung – nicht angefasst", None
            st = os.stat(fs(src))
            if formats.is_open_office_doc(src):
                return J_SKIPPED, "Datei ist gerade geoeffnet (Sperrdatei vorhanden)", None
            if run["kind"] == "archive":
                if e["sidecar"]:
                    if state_by_src.get(norm_key(e["keeper"] or "")) != J_DONE:
                        return J_SKIPPED, "zugehoerige Datei wurde nicht archiviert", None
                else:
                    ok, why = self._verify_duplicate(e, st)
                    if not ok:
                        return J_SKIPPED, why, None
                if os.path.lexists(fs(dst)):
                    new_dst = unique_path(dst)
                    self.store.journal_set(e["id"], J_PLANNED, dst=new_dst)
                    e["dst"] = dst = new_dst
            else:  # undo
                if os.path.lexists(fs(dst)):
                    return J_SKIPPED, "am Originalort existiert bereits eine Datei", None
                if e["size"] is not None and st.st_size != e["size"]:
                    return J_SKIPPED, "Archivdatei wurde veraendert", None
            h = self._move(e["id"], src, dst, e["hash"] if not e["sidecar"] else None)
            return J_DONE, None, h
        except Cancelled:
            raise
        except FileExistsError as exc:
            return J_FAILED, f"Ziel existiert bereits: {exc}", None
        except PermissionError as exc:
            return J_FAILED, f"Zugriff verweigert / Datei geoeffnet: {exc}", None
        except OSError as exc:
            return J_FAILED, str(exc), None

    def _verify_duplicate(self, e: dict, st: os.stat_result) -> tuple[bool, str]:
        src, keeper = e["src"], e["keeper"]
        if st.st_size != e["size"]:
            return False, "Groesse hat sich seit dem Scan geaendert"
        if not keeper or not os.path.isfile(fs(keeper)):
            return False, "behaltenes Original nicht mehr vorhanden – Duplikat bleibt stehen"
        if norm_key(keeper) == norm_key(src):
            return False, "Original und Duplikat sind dieselbe Datei"
        try:
            kst = os.stat(fs(keeper))
            sst = os.stat(fs(src))
            if kst.st_ino and (kst.st_dev, kst.st_ino) == (sst.st_dev, sst.st_ino):
                return False, "Hardlink auf das Original – nicht verschoben"
            if kst.st_size != e["size"]:
                return False, "Original hat sich seit dem Scan geaendert"
            if self.verify_bytes:
                if not files_equal(src, keeper, self.control, self._add_bytes):
                    return False, "Byte-Vergleich: Inhalt weicht vom Original ab"
            else:
                if hash_full(src, self.control, self._add_bytes) != e["hash"]:
                    return False, "Pruefsumme weicht vom Scan ab"
        except Cancelled:
            raise
        except OSError as exc:
            return False, f"Pruefung nicht moeglich: {exc}"
        return True, ""

    def _after_done(self, run: dict, e: dict, manifest: str, h: str | None) -> None:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        if run["kind"] == "archive":
            self._manifest_row(manifest, [now, "archiviert", e["src"], e["dst"], e["keeper"] or "",
                                          e["size"] if e["size"] is not None else "",
                                          h or e["hash"] or "", "ja" if e["sidecar"] else ""])
            if e["session_id"] and not e["sidecar"]:
                self.store.dupes_set_state(e["session_id"], e["src"], "archived")
        elif run["kind"] == "undo":
            self._manifest_row(manifest, [now, "zurueckgeholt", e["dst"], e["src"], "",
                                          e["size"] if e["size"] is not None else "",
                                          e["hash"] or "", "ja" if e["sidecar"] else ""])
            if e["ref_id"]:
                self.store.journal_set(e["ref_id"], J_UNDONE)
            if e["session_id"] and not e["sidecar"]:
                self.store.dupes_set_state(e["session_id"], e["dst"], "open")
            _remove_empty_dirs(os.path.dirname(e["src"]), run["archive"])

    # ---------------------------------------------------------------- Absturz-Wiederherstellung
    def recover_run(self, run_id: int) -> list[str]:
        """Bringt halbfertige Schritte eines Laufs in einen sauberen Zustand."""
        notes: list[str] = []
        run = self.store.run_get(run_id)
        if run and not os.path.isdir(fs(run["archive"])):
            # Archivlaufwerk nicht verbunden: nichts anfassen, spaeter erneut
            return [f"Lauf {run_id}: Archiv nicht erreichbar ({run['archive']}) – Wiederherstellung verschoben"]
        for e in self.store.journal_entries(run_id, OPEN_STATES):
            src, dst, tmp = e["src"], e["dst"], e["tmp"]
            src_ok = os.path.lexists(fs(src))
            dst_ok = os.path.lexists(fs(dst))
            try:
                if e["state"] == J_PLANNED:
                    if not src_ok and dst_ok and self._dst_plausible(e):
                        self.store.journal_set(e["id"], J_DONE)
                        notes.append(f"abgeschlossen (Umbenennung war erfolgt): {src}")
                    # sonst: bleibt PLANNED und wird normal ausgefuehrt
                elif e["state"] == J_COPYING:
                    if tmp and os.path.lexists(fs(tmp)):
                        _remove_file(tmp)
                    if dst_ok and src_ok and e["hash"] and hash_full(dst) == e["hash"]:
                        _remove_file(src)
                        self.store.journal_set(e["id"], J_DONE)
                        notes.append(f"abgeschlossen nach Kopie: {src}")
                    elif dst_ok and not src_ok:
                        self.store.journal_set(e["id"], J_DONE)
                        notes.append(f"abgeschlossen: {src}")
                    else:
                        if dst_ok and src_ok:
                            # unklarer Stand: Ziel stammt aus abgebrochener Kopie
                            if not e["hash"] or hash_full(dst) != hash_full(src):
                                _remove_file(dst)
                        self.store.journal_set(e["id"], J_PLANNED)
                        notes.append(f"Kopie verworfen, wird wiederholt: {src}")
                elif e["state"] == J_COPIED:
                    if dst_ok and src_ok:
                        if e["hash"] and hash_full(dst) == e["hash"]:
                            _remove_file(src)
                            self.store.journal_set(e["id"], J_DONE)
                            notes.append(f"Quelle nach verifizierter Kopie entfernt: {src}")
                        else:
                            _remove_file(dst)
                            self.store.journal_set(e["id"], J_PLANNED)
                            notes.append(f"Kopie ungueltig, wird wiederholt: {src}")
                    elif dst_ok:
                        self.store.journal_set(e["id"], J_DONE)
                    else:
                        self.store.journal_set(e["id"], J_FAILED if not src_ok else J_PLANNED,
                                               error=None if src_ok else "Quelle und Ziel fehlen")
            except OSError as exc:
                self.store.journal_set(e["id"], J_FAILED, error=f"Wiederherstellung: {exc}")
                notes.append(f"Fehler bei Wiederherstellung {src}: {exc}")
        for n in notes:
            log.info("Wiederherstellung Lauf %s: %s", run_id, n)
        return notes

    def _dst_plausible(self, e: dict) -> bool:
        try:
            size = os.path.getsize(fs(e["dst"]))
        except OSError:
            return False
        if e["size"] is not None and size != e["size"]:
            return False
        if e["hash"]:
            try:
                return hash_full(e["dst"]) == e["hash"]
            except OSError:
                return False
        return True

    # ---------------------------------------------------------------- Bereinigen
    def purge(self, archive_run_ids: list[int], use_trash: bool = True) -> dict:
        """Entfernt archivierte Duplikate endgueltig bzw. in den Papierkorb –
        nur nach Freigabe durch den Benutzer und nur, wenn das behaltene
        Original noch existiert."""
        stats = {"purged": 0, "kept": 0, "failed": 0, "bytes": 0}
        for rid in archive_run_ids:
            run = self.store.run_get(rid)
            if not run or run["kind"] != "archive":
                continue
            entries = self.store.journal_entries(rid, (J_DONE,))
            main_ok: dict[str, bool] = {}
            batch: list[dict] = []
            for e in entries:
                self.control.checkpoint()
                if not os.path.lexists(fs(e["dst"])):
                    stats["failed"] += 1
                    continue
                if e["sidecar"]:
                    if not main_ok.get(norm_key(e["keeper"] or ""), False):
                        stats["kept"] += 1
                        continue
                else:
                    keeper = e["keeper"]
                    ok = bool(keeper) and os.path.isfile(fs(keeper)) and (
                        e["size"] is None or os.path.getsize(fs(keeper)) == e["size"])
                    main_ok[norm_key(e["src"])] = ok
                    if not ok:
                        log.warning("Nicht entfernt (Original fehlt/geaendert): %s", e["dst"])
                        stats["kept"] += 1
                        continue
                batch.append(e)
            paths = [e["dst"] for e in batch]
            if use_trash:
                ok_paths, failed = send_to_trash(paths)
            else:
                ok_paths, failed = [], []
                for p in paths:
                    try:
                        _remove_file(p)
                        ok_paths.append(p)
                    except OSError as exc:
                        log.warning("Loeschen fehlgeschlagen %s: %s", p, exc)
                        failed.append(p)
            ok_set = {norm_key(p) for p in ok_paths}
            for e in batch:
                if norm_key(e["dst"]) in ok_set:
                    self.store.journal_set(e["id"], J_PURGED)
                    stats["purged"] += 1
                    stats["bytes"] += e["size"] or 0
                else:
                    stats["failed"] += 1
            _remove_empty_dirs_tree(run["archive"])
            self.store.run_finish(rid, "purged" if not failed else "done", run.get("stats"))
        return stats


def _remove_empty_dirs_tree(root: str) -> None:
    """Entfernt leere Unterordner im Archiv (der Archivordner selbst bleibt)."""
    root = os.path.abspath(root)
    for folder, dirs, files in os.walk(fs(root), topdown=False):
        f = unfs(folder)
        if norm_key(f) == norm_key(root) or os.path.basename(f) == MANIFEST_DIR:
            continue
        try:
            if not os.listdir(folder):
                os.rmdir(folder)
        except OSError:
            pass


def recover_all(store: Store, control: Control | None = None) -> list[str]:
    """Wird beim Programmstart aufgerufen: repariert halbfertige Schritte aller
    unterbrochenen Laeufe (setzt sie aber nicht automatisch fort)."""
    arch = Archiver(store, control or Control())
    notes: list[str] = []
    for run in store.runs_unfinished():
        notes.extend(arch.recover_run(run["id"]))
    return notes
