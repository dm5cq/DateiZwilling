"""Persistenter Zustand in SQLite (WAL, synchronous=FULL).

Enthaelt:
* Pruefsummen-Cache  – bereits berechnete Hashes werden nach einem Absturz
                       oder bei einem erneuten Scan wiederverwendet.
* Sitzungen          – Quellordner, Archiv, Optionen, Phase (fuer Fortsetzen).
* Duplikatgruppen    – Ergebnisse inkl. Auswahl "behalten/archivieren".
* Laeufe + Journal   – jeder einzelne Verschiebeschritt wird VOR und NACH der
                       Ausfuehrung protokolliert (Write-Ahead), damit nach einem
                       Absturz exakt an der Abbruchstelle weitergemacht werden kann.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Iterable

log = logging.getLogger("dateizwilling.state")

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS hash_cache (
    key TEXT PRIMARY KEY, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
    phash TEXT, fhash TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL, updated REAL,
    phase TEXT, sources TEXT, archive TEXT, options TEXT, stats TEXT);
CREATE TABLE IF NOT EXISTS dupes (
    session_id INTEGER NOT NULL, gid INTEGER NOT NULL, size INTEGER NOT NULL,
    hash TEXT NOT NULL, path TEXT NOT NULL, mtime_ns INTEGER NOT NULL,
    keep INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'open',
    kind TEXT NOT NULL DEFAULT 'same',
    PRIMARY KEY (session_id, gid, path));
CREATE INDEX IF NOT EXISTS ix_dupes_gid ON dupes(session_id, gid);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, kind TEXT,
    created REAL, finished REAL, state TEXT, archive TEXT, ref_run INTEGER,
    stats TEXT);
CREATE TABLE IF NOT EXISTS journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL,
    src TEXT NOT NULL, dst TEXT NOT NULL, tmp TEXT, size INTEGER,
    hash TEXT, keeper TEXT, sidecar INTEGER DEFAULT 0, state TEXT NOT NULL,
    error TEXT, ts REAL, ref_id INTEGER, gid INTEGER, session_id INTEGER);
CREATE INDEX IF NOT EXISTS ix_journal_run ON journal(run_id, state);
CREATE TABLE IF NOT EXISTS dup_folders (
    session_id INTEGER NOT NULL, fgid INTEGER NOT NULL, path TEXT NOT NULL,
    files INTEGER NOT NULL, size INTEGER NOT NULL, keep INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (session_id, path));
"""

MIGRATIONS = [
    ("dupes", "kind", "ALTER TABLE dupes ADD COLUMN kind TEXT NOT NULL DEFAULT 'same'"),
]

# Journal-Zustaende
J_PLANNED = "planned"      # Schritt angekuendigt, noch nichts passiert
J_COPYING = "copying"      # Kopie ueber Laufwerksgrenzen laeuft (tmp-Datei)
J_COPIED = "copied"        # Kopie vollstaendig + verifiziert, Quelle noch da
J_DONE = "done"            # erledigt (Quelle verschoben)
J_SKIPPED = "skipped"      # bewusst uebersprungen (z. B. Datei geaendert)
J_FAILED = "failed"        # Fehler, Quelle unveraendert
J_UNDONE = "undone"        # durch "Rueckgaengig" zurueckverschoben
J_PURGED = "purged"        # nach Freigabe endgueltig entfernt / Papierkorb
OPEN_STATES = (J_PLANNED, J_COPYING, J_COPIED)


class Store:
    def __init__(self, folder: str):
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, "dateizwilling.db")
        self._lock = threading.RLock()
        self.conn = self._open()

    # ------------------------------------------------------------ Verbindung
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False,
                               isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.Error:
            conn.close()
            raise
        return conn

    def _open(self) -> sqlite3.Connection:
        try:
            conn = self._connect()
            ok = conn.execute("PRAGMA quick_check").fetchone()[0]
            if ok != "ok":
                raise sqlite3.DatabaseError(ok)
        except sqlite3.DatabaseError as exc:
            log.error("Datenbank beschaedigt (%s) – wird gesichert und neu angelegt", exc)
            try:
                conn.close()  # type: ignore[possibly-undefined]
            except Exception:
                pass
            stamp = time.strftime("%Y%m%d-%H%M%S")
            for suffix in ("", "-wal", "-shm"):
                p = self.path + suffix
                if os.path.exists(p):
                    os.replace(p, f"{self.path}.defekt-{stamp}{suffix}")
            conn = self._connect()
        try:
            row = conn.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            if row and int(row[0]) < 2:
                # Ergebnislisten (keine Archivdaten) werden fuer das neue Format neu angelegt
                conn.execute("DROP TABLE IF EXISTS dupes")
        except sqlite3.Error:
            pass
        conn.executescript(SCHEMA)
        for table, col, sql in MIGRATIONS:
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                conn.execute(sql)
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('schema', ?)", (str(SCHEMA_VERSION),))
        try:  # Cache-Eintraege, die ein Jahr nicht benutzt wurden, entfernen
            conn.execute("DELETE FROM hash_cache WHERE ts < ?", (time.time() - 365 * 86400,))
        except sqlite3.Error:
            pass
        return conn

    def close(self) -> None:
        with self._lock:
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass
            self.conn.close()

    def _exec(self, sql: str, args: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self.conn.execute(sql, tuple(args))

    def _many(self, sql: str, rows: list[tuple]) -> None:
        if not rows:
            return
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.conn.executemany(sql, rows)
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    # ------------------------------------------------------------ Hash-Cache
    def cache_get(self, key: str, size: int, mtime_ns: int) -> tuple[str | None, str | None]:
        row = self._exec("SELECT size, mtime_ns, phash, fhash FROM hash_cache WHERE key=?",
                         (key,)).fetchone()
        if row and row[0] == size and row[1] == mtime_ns:
            return row[2], row[3]
        return None, None

    def cache_put_many(self, rows: list[tuple[str, int, int, str | None, str | None]]) -> None:
        now = time.time()
        self._many(
            "INSERT INTO hash_cache(key,size,mtime_ns,phash,fhash,ts) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET size=excluded.size, mtime_ns=excluded.mtime_ns, "
            "phash=COALESCE(excluded.phash, CASE WHEN hash_cache.size=excluded.size AND "
            "hash_cache.mtime_ns=excluded.mtime_ns THEN hash_cache.phash END), "
            "fhash=COALESCE(excluded.fhash, CASE WHEN hash_cache.size=excluded.size AND "
            "hash_cache.mtime_ns=excluded.mtime_ns THEN hash_cache.fhash END), ts=excluded.ts",
            [(k, s, m, p, f, now) for k, s, m, p, f in rows])

    def cache_clear(self) -> None:
        self._exec("DELETE FROM hash_cache")

    def cache_count(self) -> int:
        return self._exec("SELECT COUNT(*) FROM hash_cache").fetchone()[0]

    # ------------------------------------------------------------ Sitzungen
    def session_create(self, sources: list[str], archive: str, options: dict) -> int:
        now = time.time()
        cur = self._exec(
            "INSERT INTO sessions(created,updated,phase,sources,archive,options,stats) "
            "VALUES (?,?,?,?,?,?,?)",
            (now, now, "scanning", json.dumps(sources), archive, json.dumps(options), "{}"))
        return int(cur.lastrowid)

    def session_update(self, sid: int, phase: str | None = None, stats: dict | None = None) -> None:
        if phase is not None:
            self._exec("UPDATE sessions SET phase=?, updated=? WHERE id=?", (phase, time.time(), sid))
        if stats is not None:
            self._exec("UPDATE sessions SET stats=?, updated=? WHERE id=?",
                       (json.dumps(stats), time.time(), sid))

    def session_get(self, sid: int) -> dict | None:
        row = self._exec("SELECT id,created,updated,phase,sources,archive,options,stats "
                         "FROM sessions WHERE id=?", (sid,)).fetchone()
        return self._session_row(row) if row else None

    def session_latest(self) -> dict | None:
        row = self._exec("SELECT id,created,updated,phase,sources,archive,options,stats "
                         "FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
        return self._session_row(row) if row else None

    @staticmethod
    def _session_row(row: tuple) -> dict:
        return {
            "id": row[0], "created": row[1], "updated": row[2], "phase": row[3],
            "sources": json.loads(row[4] or "[]"), "archive": row[5],
            "options": json.loads(row[6] or "{}"), "stats": json.loads(row[7] or "{}"),
        }

    # ------------------------------------------------------------ Duplikate
    def dupes_store(self, sid: int, groups: list[dict]) -> None:
        rows = []
        for g in groups:
            for m in g["members"]:
                rows.append((sid, g["gid"], m.get("size", g["size"]), g["hash"], m["path"],
                             m["mtime_ns"], 1 if m.get("keep") else 0, g.get("kind", "same")))
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.conn.execute("DELETE FROM dupes WHERE session_id=?", (sid,))
                self.conn.executemany(
                    "INSERT OR IGNORE INTO dupes(session_id,gid,size,hash,path,mtime_ns,keep,kind) "
                    "VALUES (?,?,?,?,?,?,?,?)", rows)
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def dupes_load(self, sid: int) -> list[dict]:
        rows = self._exec("SELECT gid,size,hash,path,mtime_ns,keep,state,kind FROM dupes "
                          "WHERE session_id=? ORDER BY gid, path", (sid,)).fetchall()
        groups: dict[int, dict] = {}
        for gid, size, h, path, mt, keep, state, kind in rows:
            g = groups.setdefault(gid, {"gid": gid, "size": size, "hash": h, "kind": kind or "same",
                                        "members": []})
            g["members"].append({"path": path, "mtime_ns": mt, "keep": bool(keep), "state": state,
                                 "size": size})
            g["size"] = max(g["size"], size)
        return list(groups.values())

    # ------------------------------------------------------------ doppelte Ordner
    def folders_store(self, sid: int, fgroups: list[dict]) -> None:
        rows = [(sid, fg["fgid"], f["path"], f["files"], f["size"], 1 if f.get("keep") else 0)
                for fg in fgroups for f in fg["folders"]]
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.conn.execute("DELETE FROM dup_folders WHERE session_id=?", (sid,))
                self.conn.executemany("INSERT OR IGNORE INTO dup_folders VALUES (?,?,?,?,?,?)", rows)
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def folders_load(self, sid: int) -> list[dict]:
        out: dict[int, dict] = {}
        for fgid, path, files, size, keep in self._exec(
                "SELECT fgid,path,files,size,keep FROM dup_folders WHERE session_id=? ORDER BY fgid,path",
                (sid,)).fetchall():
            fg = out.setdefault(fgid, {"fgid": fgid, "files": files, "size": size, "folders": []})
            fg["folders"].append({"path": path, "files": files, "size": size, "keep": bool(keep)})
        return list(out.values())

    # ------------------------------------------------------------ Wartung / Sicherung
    def maintenance(self, force: bool = False, keep_sessions: int = 10,
                    cache_cap: int = 3_000_000) -> bool:
        """Woechentliche Pflege: alte Sitzungen, Cache-Obergrenze, Optimierung."""
        row = self._exec("SELECT value FROM meta WHERE key='last_maint'").fetchone()
        last = float(row[0]) if row else 0.0
        if not force and time.time() - last < 7 * 86400:
            return False
        try:
            ids = [r[0] for r in self._exec("SELECT id FROM sessions ORDER BY id DESC").fetchall()]
            old = ids[keep_sessions:]
            if old:
                q = ",".join("?" * len(old))
                self._exec(f"DELETE FROM dupes WHERE session_id IN ({q})", old)
                self._exec(f"DELETE FROM dup_folders WHERE session_id IN ({q})", old)
            n = self.cache_count()
            if n > cache_cap:
                self._exec("DELETE FROM hash_cache WHERE key IN (SELECT key FROM hash_cache "
                           "ORDER BY ts LIMIT ?)", (n - cache_cap,))
            self._exec("PRAGMA optimize")
            pages = self._exec("PRAGMA page_count").fetchone()[0]
            free = self._exec("PRAGMA freelist_count").fetchone()[0]
            if pages and free / pages > 0.25:
                self._exec("VACUUM")
            self._exec("INSERT OR REPLACE INTO meta VALUES ('last_maint', ?)", (str(time.time()),))
            log.info("Datenbankpflege durchgefuehrt (%s Cache-Eintraege)", min(n, cache_cap))
            return True
        except sqlite3.Error as exc:
            log.warning("Datenbankpflege fehlgeschlagen: %s", exc)
            return False

    def backup_to(self, dest: str) -> bool:
        """Konsistente Kopie der Datenbank (SQLite-Backup-API), atomar ersetzt."""
        tmp = dest + ".tmp"
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.exists(tmp):
                os.remove(tmp)
            target = sqlite3.connect(tmp)
            try:
                with self._lock:
                    self.conn.backup(target)
            finally:
                target.close()
            os.replace(tmp, dest)
            return True
        except (sqlite3.Error, OSError) as exc:
            log.warning("Datenbanksicherung nach %s fehlgeschlagen: %s", dest, exc)
            return False

    def meta_get(self, key: str, default: str | None = None) -> str | None:
        row = self._exec("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def meta_set(self, key: str, value: str) -> None:
        self._exec("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, value))

    def dupes_set_keep(self, sid: int, path: str, keep: bool, gid: int | None = None) -> None:
        if gid is None:
            self._exec("UPDATE dupes SET keep=? WHERE session_id=? AND path=?",
                       (1 if keep else 0, sid, path))
        else:
            self._exec("UPDATE dupes SET keep=? WHERE session_id=? AND gid=? AND path=?",
                       (1 if keep else 0, sid, gid, path))

    def dupes_set_state(self, sid: int, path: str, state: str) -> None:
        self._exec("UPDATE dupes SET state=? WHERE session_id=? AND path=?", (state, sid, path))

    # ------------------------------------------------------------ Laeufe/Journal
    def run_create(self, sid: int | None, kind: str, archive: str, ref_run: int | None = None) -> int:
        cur = self._exec("INSERT INTO runs(session_id,kind,created,state,archive,ref_run,stats) "
                         "VALUES (?,?,?,?,?,?,?)",
                         (sid, kind, time.time(), "running", archive, ref_run, "{}"))
        return int(cur.lastrowid)

    def run_finish(self, run_id: int, state: str = "done", stats: dict | None = None) -> None:
        self._exec("UPDATE runs SET state=?, finished=?, stats=? WHERE id=?",
                   (state, time.time(), json.dumps(stats or {}), run_id))

    def run_get(self, run_id: int) -> dict | None:
        row = self._exec("SELECT id,session_id,kind,created,finished,state,archive,ref_run,stats "
                         "FROM runs WHERE id=?", (run_id,)).fetchone()
        return self._run_row(row) if row else None

    def runs_list(self, kind: str | None = None, limit: int = 50) -> list[dict]:
        if kind:
            rows = self._exec("SELECT id,session_id,kind,created,finished,state,archive,ref_run,stats "
                              "FROM runs WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, limit))
        else:
            rows = self._exec("SELECT id,session_id,kind,created,finished,state,archive,ref_run,stats "
                              "FROM runs ORDER BY id DESC LIMIT ?", (limit,))
        return [self._run_row(r) for r in rows.fetchall()]

    def runs_unfinished(self) -> list[dict]:
        rows = self._exec("SELECT id,session_id,kind,created,finished,state,archive,ref_run,stats "
                          "FROM runs WHERE state='running' ORDER BY id").fetchall()
        return [self._run_row(r) for r in rows]

    @staticmethod
    def _run_row(row: tuple) -> dict:
        return {"id": row[0], "session_id": row[1], "kind": row[2], "created": row[3],
                "finished": row[4], "state": row[5], "archive": row[6], "ref_run": row[7],
                "stats": json.loads(row[8] or "{}")}

    def journal_plan(self, run_id: int, rows: list[dict]) -> None:
        """Schreibt den kompletten Plan eines Laufs in EINER Transaktion."""
        now = time.time()
        self._many(
            "INSERT INTO journal(run_id,src,dst,size,hash,keeper,sidecar,state,ts,ref_id,gid,session_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [(run_id, r["src"], r["dst"], r.get("size"), r.get("hash"), r.get("keeper"),
              1 if r.get("sidecar") else 0, J_PLANNED, now, r.get("ref_id"), r.get("gid"),
              r.get("session_id")) for r in rows])

    def journal_set(self, jid: int, state: str, error: str | None = None,
                    dst: str | None = None, tmp: str | None = None, h: str | None = None) -> None:
        sets, args = ["state=?", "ts=?"], [state, time.time()]
        if error is not None:
            sets.append("error=?"); args.append(error[:500])
        if dst is not None:
            sets.append("dst=?"); args.append(dst)
        if tmp is not None:
            sets.append("tmp=?"); args.append(tmp)
        if h is not None:
            sets.append("hash=?"); args.append(h)
        args.append(jid)
        self._exec(f"UPDATE journal SET {', '.join(sets)} WHERE id=?", args)

    def journal_entries(self, run_id: int, states: tuple[str, ...] | None = None) -> list[dict]:
        sql = ("SELECT id,run_id,src,dst,tmp,size,hash,keeper,sidecar,state,error,ts,ref_id,gid,"
               "session_id FROM journal WHERE run_id=?")
        args: list[Any] = [run_id]
        if states:
            sql += " AND state IN (%s)" % ",".join("?" * len(states))
            args.extend(states)
        sql += " ORDER BY id"
        rows = self._exec(sql, args).fetchall()
        keys = ("id", "run_id", "src", "dst", "tmp", "size", "hash", "keeper", "sidecar",
                "state", "error", "ts", "ref_id", "gid", "session_id")
        return [dict(zip(keys, r)) for r in rows]

    def journal_open_count(self) -> int:
        return self._exec("SELECT COUNT(*) FROM journal j JOIN runs r ON r.id=j.run_id "
                          "WHERE r.state='running' OR j.state IN (?,?,?)",
                          OPEN_STATES).fetchone()[0]



class ScanTemp:
    """Datei-Liste eines Scans auf der Festplatte statt im Arbeitsspeicher (ST4).
    Damit bleiben auch Laufwerke mit vielen Millionen Dateien beherrschbar."""

    def __init__(self, folder: str, sid: int):
        self.path = os.path.join(folder, f"scan-temp-{sid}.db")
        for suffix in ("", "-wal", "-shm", "-journal"):
            try:
                os.remove(self.path + suffix)
            except OSError:
                pass
        self.conn = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=OFF")
        self.conn.execute("PRAGMA synchronous=OFF")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("CREATE TABLE files (key TEXT PRIMARY KEY, path TEXT, dir TEXT, size INTEGER, "
                          "mtime_ns INTEGER)")
        self.count = 0
        self._buf: list[tuple] = []

    def add(self, key: str, path: str, size: int, mtime_ns: int) -> None:
        self._buf.append((key, path, os.path.dirname(path), size, mtime_ns))
        if len(self._buf) >= 5000:
            self.flush()

    def flush(self) -> None:
        if self._buf:
            self.conn.execute("BEGIN")
            cur = self.conn.executemany("INSERT OR IGNORE INTO files VALUES (?,?,?,?,?)", self._buf)
            self.conn.execute("COMMIT")
            self.count += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            self._buf = []

    def total(self) -> int:
        self.flush()
        return self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    def candidates(self):
        """Dateien, deren Groesse mehrfach vorkommt – gruppiert nach Groesse."""
        self.flush()
        self.conn.execute("CREATE INDEX IF NOT EXISTS ix_size ON files(size)")
        cur = self.conn.execute(
            "SELECT path, size, mtime_ns FROM files WHERE size IN "
            "(SELECT size FROM files GROUP BY size HAVING COUNT(*) > 1) ORDER BY size")
        group: list[tuple] = []
        last = None
        for row in cur:
            if row[1] != last and group:
                yield group
                group = []
            last = row[1]
            group.append(row)
        if group:
            yield group

    def iter_paths(self, exts: set[str] | None = None):
        self.flush()
        for path, size, mt in self.conn.execute("SELECT path, size, mtime_ns FROM files"):
            if exts is None or path.rsplit(".", 1)[-1].lower() in exts:
                yield path, size, mt

    def dir_counts(self) -> dict[str, tuple[int, int]]:
        """Anzahl und Groesse aller Dateien je Ordner (rekursiv aufsummiert)."""
        self.flush()
        out: dict[str, list[int]] = {}
        for d, n, sz in self.conn.execute("SELECT dir, COUNT(*), SUM(size) FROM files GROUP BY dir"):
            cur = d
            while True:
                e = out.setdefault(cur, [0, 0])
                e[0] += n
                e[1] += sz or 0
                parent = os.path.dirname(cur)
                if parent == cur or not parent:
                    break
                cur = parent
        return {k: (v[0], v[1]) for k, v in out.items()}

    def close(self) -> None:
        try:
            self.conn.close()
        finally:
            for suffix in ("", "-wal", "-shm", "-journal"):
                try:
                    os.remove(self.path + suffix)
                except OSError:
                    pass
