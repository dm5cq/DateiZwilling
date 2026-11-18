"""Scan-Engine: findet inhaltsgleiche Dateien in mehreren Stufen.

1. Verzeichnisse durchlaufen (ohne Symlinks/Junctions, ohne Archiv,
   ohne System-/Paketordner, optional ohne Cloud-Platzhalter).
2. Nach exakter Dateigroesse gruppieren – nur gleich grosse Dateien koennen
   identisch sein. Hardlinks (dieselbe physische Datei) werden ausgesondert.
3. Schnell-Pruefsumme (Anfang + Ende, BLAKE2b).
4. Volle Pruefsumme (BLAKE2b-256) nur fuer verbleibende Kandidaten.
5. Gruppen bilden und je Gruppe das zu behaltende Original bestimmen.

Alle berechneten Pruefsummen landen laufend im Cache der Datenbank. Stuerzt
die App ab oder wird abgebrochen, startet der naechste Scan an derselben
Stelle: bereits gepruefte Dateien werden nicht erneut gelesen.
"""
from __future__ import annotations

import fnmatch
import logging
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field

from . import formats
from .common import (SMALL_FILE, Cancelled, Control, ProgressFn, RateMeter, hash_full,
                     hash_partial)
from .pathutil import fs, is_cloud_only, is_hidden, is_within, norm_key, unfs
from .state import Store

log = logging.getLogger("dateizwilling.scan")

KEEP_RULES = ("oldest", "newest", "shortest", "longest")


@dataclass
class ScanOptions:
    sources: list[str] = field(default_factory=list)
    archive: str = ""
    protected: list[str] = field(default_factory=list)
    excludes: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)   # leer = alle
    min_size: int = 1
    max_size: int = 0                                     # 0 = unbegrenzt
    include_hidden: bool = False
    skip_cloud_only: bool = True
    protect_catalogs: bool = True
    prefer_source_order: bool = True
    keep_rule: str = "oldest"
    workers: int = 2
    verify_bytes: bool = True
    move_sidecars: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "ScanOptions":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class FileRec:
    path: str
    size: int
    mtime_ns: int
    phash: str | None = None
    fhash: str | None = None


def validate_options(opts: ScanOptions) -> list[str]:
    """Liefert Fehlermeldungs-Schluessel (leer = alles in Ordnung)."""
    errs: list[str] = []
    if not opts.sources:
        errs.append("err_no_sources")
    for s in opts.sources:
        if not os.path.isdir(fs(s)):
            errs.append("err_source_missing:" + s)
    if not opts.archive:
        errs.append("err_no_archive")
    else:
        for s in opts.sources:
            if is_within(s, opts.archive):
                errs.append("err_source_in_archive:" + s)
    if opts.keep_rule not in KEEP_RULES:
        errs.append("err_keep_rule")
    return errs


class Scanner:
    def __init__(self, store: Store, control: Control, progress: ProgressFn | None = None):
        self.store = store
        self.control = control
        self.progress = progress or (lambda d: None)
        self.errors: list[tuple[str, str]] = []
        self.stats: dict = {}

    # ---------------------------------------------------------------- Hilfen
    def _emit(self, **kw) -> None:
        try:
            self.progress(kw)
        except Exception:  # Fortschrittsanzeige darf nie den Scan stoppen
            log.exception("Fortschrittsrueckmeldung fehlgeschlagen")

    def _err(self, path: str, exc: BaseException | str) -> None:
        msg = str(exc)
        self.errors.append((path, msg))
        if len(self.errors) <= 2000:
            log.warning("%s: %s", path, msg)

    # ---------------------------------------------------------------- Phase 1
    def enumerate(self, opts: ScanOptions) -> list[FileRec]:
        roots: list[str] = []
        for s in opts.sources:
            a = os.path.abspath(unfs(s))
            if any(is_within(a, r) for r in roots):
                continue  # verschachtelt – bereits enthalten
            roots = [r for r in roots if not is_within(r, a)]
            roots.append(a)
        archive_key = norm_key(opts.archive) if opts.archive else None
        excl = [e.strip().lower() for e in opts.excludes if e.strip()]
        cats = set(opts.categories or [])
        files: list[FileRec] = []
        seen: set[str] = set()
        last = 0.0
        dirs_done = 0
        for root in roots:
            stack = [root]
            while stack:
                self.control.checkpoint()
                folder = stack.pop()
                dirs_done += 1
                try:
                    it = os.scandir(fs(folder))
                except OSError as exc:
                    self._err(folder, exc)
                    continue
                with it:
                    for entry in it:
                        name = entry.name
                        full = os.path.join(folder, name)
                        try:
                            if entry.is_symlink() or (hasattr(entry, "is_junction") and entry.is_junction()):
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                if formats.is_skipped_dir(name) or formats.is_protected_container(name):
                                    continue
                                if archive_key and norm_key(full) == archive_key:
                                    continue
                                if not opts.include_hidden and is_hidden(name, entry.stat(follow_symlinks=False)):
                                    continue
                                if excl and self._excluded(full, name, excl):
                                    continue
                                stack.append(full)
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                continue
                            if formats.is_skipped_file(name):
                                continue
                            if opts.protect_catalogs and formats.is_protected_file(name):
                                continue
                            if cats and formats.category_of(name) not in cats:
                                continue
                            if excl and self._excluded(full, name, excl):
                                continue
                            st = entry.stat(follow_symlinks=False)
                            if not opts.include_hidden and is_hidden(name, st):
                                continue
                            if st.st_size < max(0, opts.min_size):
                                continue
                            if opts.max_size and st.st_size > opts.max_size:
                                continue
                            if opts.skip_cloud_only and is_cloud_only(st):
                                continue
                            key = norm_key(full)
                            if key in seen:
                                continue
                            seen.add(key)
                            files.append(FileRec(full, st.st_size, st.st_mtime_ns))
                        except OSError as exc:
                            self._err(full, exc)
                now = time.monotonic()
                if now - last > 0.25:
                    last = now
                    self._emit(phase="enumerate", files=len(files), dirs=dirs_done, current=folder)
        self._emit(phase="enumerate", files=len(files), dirs=dirs_done, current="")
        return files

    @staticmethod
    def _excluded(full: str, name: str, patterns: list[str]) -> bool:
        low_name = name.lower()
        low_full = full.lower().replace("\\", "/")
        for p in patterns:
            pp = p.replace("\\", "/")
            if fnmatch.fnmatchcase(low_name, pp) or fnmatch.fnmatchcase(low_full, pp):
                return True
        return False

    # ---------------------------------------------------------------- Phase 2
    def _drop_hardlinks(self, group: list[FileRec]) -> list[FileRec]:
        seen: dict[tuple[int, int], FileRec] = {}
        out: list[FileRec] = []
        for rec in group:
            try:
                st = os.stat(fs(rec.path), follow_symlinks=False)
            except OSError as exc:
                self._err(rec.path, exc)
                continue
            if st.st_size != rec.size:
                self._err(rec.path, "Datei hat sich waehrend des Scans geaendert – uebersprungen")
                continue
            # Zeitstempel aus os.stat uebernehmen: Verzeichniseintraege mancher
            # Netzlaufwerke liefern abweichende Werte – so bleiben alle spaeteren
            # Vergleiche und der Cache konsistent.
            rec.mtime_ns = st.st_mtime_ns
            ident = (st.st_dev, st.st_ino)
            if st.st_ino and ident in seen:
                log.info("Hardlink (gleiche physische Datei) ignoriert: %s = %s",
                         rec.path, seen[ident].path)
                continue
            seen[ident] = rec
            out.append(rec)
        return out

    # ---------------------------------------------------------------- Hashing
    def _hash_stage(self, recs: list[FileRec], full: bool, workers: int,
                    total_bytes: int, phase: str) -> None:
        """Berechnet (Schnell- bzw. volle) Pruefsummen parallel, mit Cache."""
        pending: list[FileRec] = []
        done_bytes = 0
        done_files = 0
        for rec in recs:
            ph, fh = self.store.cache_get(norm_key(rec.path), rec.size, rec.mtime_ns)
            if full:
                if not fh:
                    pending.append(rec)
                    continue
                rec.fhash = fh
            elif rec.size <= SMALL_FILE:
                if not fh:
                    pending.append(rec)
                    continue
                rec.phash = rec.fhash = fh
            else:
                if not ph:
                    pending.append(rec)
                    continue
                rec.phash = ph
                if fh:
                    rec.fhash = fh
            done_files += 1
            done_bytes += rec.size if full else min(rec.size, 128 * 1024)
        cached = done_files
        meter = RateMeter()
        buf: list[tuple] = []
        last_flush = time.monotonic()
        last_emit = 0.0
        byte_counter = [done_bytes]

        def add_bytes(n: int) -> None:
            byte_counter[0] += n

        def work(rec: FileRec) -> tuple[FileRec, str | None, str | None, str | None]:
            try:
                st0 = os.stat(fs(rec.path))
                if st0.st_size != rec.size or st0.st_mtime_ns != rec.mtime_ns:
                    return rec, None, None, "changed"
                if full:
                    h = hash_full(rec.path, self.control, add_bytes)
                    ph, fh = None, h
                else:
                    h, is_full = hash_partial(rec.path, rec.size, self.control)
                    add_bytes(min(rec.size, 128 * 1024))
                    ph, fh = h, (h if is_full else None)
                st1 = os.stat(fs(rec.path))
                if st1.st_size != rec.size or st1.st_mtime_ns != rec.mtime_ns:
                    return rec, None, None, "changed"
                return rec, ph, fh, None
            except Cancelled:
                raise
            except OSError as exc:
                return rec, None, None, str(exc)

        def flush() -> None:
            nonlocal buf, last_flush
            if buf:
                self.store.cache_put_many(buf)
                buf = []
            last_flush = time.monotonic()

        workers = max(1, min(int(workers or 1), 16))
        try:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="dz-hash") as pool:
                it = iter(pending)
                running: set = set()
                exhausted = False
                while running or not exhausted:
                    while not exhausted and len(running) < workers * 4:
                        try:
                            running.add(pool.submit(work, next(it)))
                        except StopIteration:
                            exhausted = True
                    if not running:
                        break
                    done, running = wait(running, timeout=0.3, return_when=FIRST_COMPLETED)
                    for fut in done:
                        try:
                            rec, ph, fh, err = fut.result()
                        except Cancelled:
                            for f in running:
                                f.cancel()
                            raise
                        done_files += 1
                        if err == "changed":
                            self._err(rec.path, "Datei hat sich waehrend des Scans geaendert – uebersprungen")
                            rec.phash = rec.fhash = None
                            rec.size = -1  # aussortieren
                            continue
                        if err:
                            self._err(rec.path, err)
                            rec.size = -1
                            continue
                        if full:
                            rec.fhash = fh
                        else:
                            rec.phash = ph
                            if fh:
                                rec.fhash = fh
                        buf.append((norm_key(rec.path), rec.size, rec.mtime_ns, ph, fh))
                    if len(buf) >= 300 or time.monotonic() - last_flush > 2.0:
                        flush()
                    now = time.monotonic()
                    if now - last_emit > 0.25:
                        last_emit = now
                        meter.update(byte_counter[0])
                        self._emit(phase=phase, files=done_files, total=len(recs),
                                   bytes=byte_counter[0], total_bytes=total_bytes,
                                   rate=meter.rate(), eta=meter.eta(total_bytes - byte_counter[0]),
                                   cached=cached)
                    self.control.checkpoint()
        finally:
            flush()  # bereits Berechnetes bleibt auch bei Absturz/Abbruch erhalten
        self._emit(phase=phase, files=done_files, total=len(recs), bytes=total_bytes,
                   total_bytes=total_bytes, rate=meter.rate(), eta=0, cached=cached)

    # ---------------------------------------------------------------- Gesamtlauf
    def run(self, opts: ScanOptions, session_id: int | None = None) -> tuple[int, list[dict]]:
        t0 = time.time()
        if session_id is None:
            session_id = self.store.session_create(opts.sources, opts.archive, opts.to_dict())
        else:
            self.store.session_update(session_id, phase="scanning")
        log.info("Scan gestartet (Sitzung %s): %s", session_id, opts.sources)

        files = self.enumerate(opts)
        by_size: dict[int, list[FileRec]] = {}
        for rec in files:
            by_size.setdefault(rec.size, []).append(rec)
        cands: list[FileRec] = []
        for size, grp in by_size.items():
            if len(grp) < 2:
                continue
            grp = self._drop_hardlinks(grp)
            if len(grp) >= 2:
                cands.extend(grp)
        self.control.checkpoint()

        # Schnell-Pruefsumme
        partial_bytes = sum(min(r.size, 128 * 1024) for r in cands)
        self._hash_stage(cands, full=False, workers=opts.workers,
                         total_bytes=partial_bytes, phase="partial")
        by_partial: dict[tuple[int, str], list[FileRec]] = {}
        for r in cands:
            if r.size >= 0 and r.phash:
                by_partial.setdefault((r.size, r.phash), []).append(r)
        full_cands = [r for g in by_partial.values() if len(g) >= 2 for r in g]
        need_full = [r for r in full_cands if not r.fhash]
        self.control.checkpoint()

        # Volle Pruefsumme
        self._hash_stage(need_full, full=True, workers=opts.workers,
                         total_bytes=sum(r.size for r in need_full), phase="full")
        by_full: dict[tuple[int, str], list[FileRec]] = {}
        for r in full_cands:
            if r.size >= 0 and r.fhash:
                by_full.setdefault((r.size, r.fhash), []).append(r)

        groups: list[dict] = []
        for (size, h), recs in by_full.items():
            if len(recs) < 2:
                continue
            members = [{"path": r.path, "mtime_ns": r.mtime_ns, "keep": False} for r in recs]
            choose_keepers(members, opts)
            groups.append({"size": size, "hash": h, "members": members})
        groups.sort(key=lambda g: (-(g["size"] * (len(g["members"]) - 1)), g["members"][0]["path"]))
        for i, g in enumerate(groups, 1):
            g["gid"] = i

        self.store.dupes_store(session_id, groups)
        wasted = sum(g["size"] * sum(1 for m in g["members"] if not m["keep"]) for g in groups)
        self.stats = {
            "files": len(files), "candidates": len(cands), "groups": len(groups),
            "duplicates": sum(sum(1 for m in g["members"] if not m["keep"]) for g in groups),
            "wasted": wasted, "errors": len(self.errors), "seconds": round(time.time() - t0, 1),
        }
        self.store.session_update(session_id, phase="review", stats=self.stats)
        log.info("Scan fertig: %s", self.stats)
        return session_id, groups


def _priority(path: str, opts: ScanOptions) -> int:
    for i, s in enumerate(opts.sources):
        if is_within(path, s):
            return i
    return len(opts.sources)


def choose_keepers(members: list[dict], opts: ScanOptions) -> None:
    """Setzt 'keep' fuer genau ein Original je Gruppe – bzw. fuer alle
    Dateien in geschuetzten Ordnern (die werden nie archiviert)."""
    for m in members:
        m["keep"] = False
    protected = [m for m in members if any(is_within(m["path"], p) for p in opts.protected if p)]
    if protected:
        for m in protected:
            m["keep"] = True
        return

    def rule_key(m: dict):
        p = m["path"]
        if opts.keep_rule == "newest":
            k = -m["mtime_ns"]
        elif opts.keep_rule == "shortest":
            k = len(p)
        elif opts.keep_rule == "longest":
            k = -len(p)
        else:
            k = m["mtime_ns"]
        prio = _priority(p, opts) if opts.prefer_source_order else 0
        return (prio, k, len(p), p.lower())

    min(members, key=rule_key)["keep"] = True
