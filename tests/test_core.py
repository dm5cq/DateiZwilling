"""Automatische Tests der Kern-Engine (ohne Oberflaeche).

Start:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import errno
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dateizwilling import archiver as archmod  # noqa: E402
from dateizwilling.archiver import Archiver, recover_all  # noqa: E402
from dateizwilling.common import Cancelled, Control  # noqa: E402
from dateizwilling.pathutil import archive_target  # noqa: E402
from dateizwilling.scanner import ScanOptions, Scanner, validate_options  # noqa: E402
from dateizwilling.state import J_COPIED, J_DONE, J_PLANNED, J_SKIPPED, J_UNDONE, Store  # noqa: E402


def w(path: str, data: bytes, mtime: float | None = None) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    if mtime:
        os.utime(path, (mtime, mtime))
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dz_test_")
        self.src1 = os.path.join(self.tmp, "Quelle1")
        self.src2 = os.path.join(self.tmp, "Quelle2")
        self.arch = os.path.join(self.tmp, "Archiv")
        self.store = Store(os.path.join(self.tmp, "daten"))
        self.big = os.urandom(300_000)
        self.big2 = bytearray(self.big)
        self.big2[150_000] ^= 0xFF  # gleiche Groesse, gleicher Anfang/Ende, anderer Inhalt
        self.big2 = bytes(self.big2)
        w(os.path.join(self.src1, "Vertrag.docx"), self.big, 1_600_000_000)
        w(os.path.join(self.src2, "Ordner A", "Vertrag Kopie.docx"), self.big, 1_700_000_000)
        w(os.path.join(self.src2, "Ordner B", "nochmal.docx"), self.big, 1_650_000_000)
        w(os.path.join(self.src2, "anders.docx"), self.big2)           # nur scheinbar gleich
        w(os.path.join(self.src1, "klein.txt"), b"hallo welt")
        w(os.path.join(self.src2, "klein-kopie.txt"), b"hallo welt")
        w(os.path.join(self.src1, "leer1.txt"), b"")
        w(os.path.join(self.src2, "leer2.txt"), b"")
        w(os.path.join(self.src1, "~$Vertrag.docx"), b"hallo welt")    # Office-Sperrdatei

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def opts(self, **kw) -> ScanOptions:
        base = dict(sources=[self.src1, self.src2], archive=self.arch, workers=2)
        base.update(kw)
        return ScanOptions(**base)

    def scan(self, **kw):
        return Scanner(self.store, Control()).run(self.opts(**kw))


class ScanTests(Base):
    def test_groups(self):
        sid, groups = self.scan()
        self.assertEqual(len(groups), 2)
        big = [g for g in groups if g["size"] == 300_000][0]
        self.assertEqual(len(big["members"]), 3)
        self.assertNotIn("anders.docx", str(big["members"]))
        keepers = [m for m in big["members"] if m["keep"]]
        self.assertEqual(len(keepers), 1)
        self.assertTrue(keepers[0]["path"].endswith(os.path.join("Quelle1", "Vertrag.docx")))
        paths = str(groups)
        self.assertNotIn("leer", paths)          # leere Dateien ignoriert
        self.assertNotIn("~$", paths)            # Sperrdateien ignoriert

    def test_keep_newest_without_priority(self):
        _, groups = self.scan(keep_rule="newest", prefer_source_order=False)
        big = [g for g in groups if g["size"] == 300_000][0]
        k = [m for m in big["members"] if m["keep"]][0]
        self.assertIn("Vertrag Kopie.docx", k["path"])

    def test_protected_folder(self):
        _, groups = self.scan(protected=[self.src2])
        big = [g for g in groups if g["size"] == 300_000][0]
        for m in big["members"]:
            self.assertEqual(m["keep"], self.src2 in m["path"])

    def test_hardlink_and_symlink_ignored(self):
        h = os.path.join(self.src1, "hardlink.docx")
        os.link(os.path.join(self.src1, "Vertrag.docx"), h)
        try:
            os.symlink(os.path.join(self.src1, "Vertrag.docx"), os.path.join(self.src1, "sym.docx"))
        except (OSError, NotImplementedError):
            pass  # Windows ohne Entwicklermodus: keine Symlinks erlaubt
        _, groups = self.scan()
        big = [g for g in groups if g["size"] == 300_000][0]
        names = [os.path.basename(m["path"]) for m in big["members"]]
        self.assertEqual(len(big["members"]), 3)
        self.assertNotIn("sym.docx", names)

    def test_archive_inside_source_is_excluded(self):
        inner = os.path.join(self.src1, "Archiv")
        w(os.path.join(inner, "alt", "Vertrag.docx"), self.big)
        _, groups = self.scan(archive=inner)
        self.assertNotIn(inner, str(groups))

    def test_nested_sources(self):
        _, groups = self.scan(sources=[self.tmp + os.sep + "Quelle2", self.src2])
        big = [g for g in groups if g["size"] == 300_000][0]
        self.assertEqual(len(big["members"]), 2)

    def test_validate(self):
        self.assertIn("err_no_sources", validate_options(ScanOptions(archive=self.arch)))
        errs = validate_options(ScanOptions(sources=[self.arch + "/x"], archive=self.arch))
        self.assertTrue(any(e.startswith("err_source") for e in errs))

    def test_category_filter(self):
        _, groups = self.scan(categories=["text"])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["size"], 10)

    def test_scan_resume_uses_cache(self):
        ctl = Control()
        calls = {"n": 0}
        real = archmod.hash_full

        def boom(*a, **k):
            calls["n"] += 1
            raise Cancelled()
        sc = Scanner(self.store, ctl)
        with mock.patch("dateizwilling.scanner.hash_full", side_effect=boom):
            with self.assertRaises(Cancelled):
                sc.run(self.opts())
        self.assertEqual(self.store.session_latest()["phase"], "scanning")
        # Schnell-Pruefsummen sind bereits im Cache
        self.assertGreater(self.store.cache_count(), 0)
        sid = self.store.session_latest()["id"]
        sid2, groups = Scanner(self.store, Control()).run(self.opts(), sid)
        self.assertEqual(sid, sid2)
        self.assertEqual(len(groups), 2)
        # zweiter Scan liest nichts mehr neu
        with mock.patch("dateizwilling.scanner.hash_full", side_effect=AssertionError("neu gelesen")), \
                mock.patch("dateizwilling.scanner.hash_partial", side_effect=AssertionError("neu gelesen")):
            _, groups2 = Scanner(self.store, Control()).run(self.opts())
        self.assertEqual(len(groups2), 2)
        self.assertTrue(real)


class ArchiveTests(Base):
    def archive(self, verify=True, **kw):
        sid, groups = self.scan(**kw)
        arch = Archiver(self.store, Control(), verify_bytes=verify)
        rid = arch.plan_archive(sid, groups, self.arch)
        return sid, rid, arch, arch.execute(rid)

    def test_archive_mirrors_paths(self):
        _, rid, _, stats = self.archive()
        self.assertEqual(stats["done"], 3)
        dup = os.path.join(self.src2, "Ordner A", "Vertrag Kopie.docx")
        self.assertFalse(os.path.exists(dup))
        tgt = archive_target(self.arch, dup)
        self.assertTrue(os.path.isfile(tgt))
        self.assertTrue(tgt.startswith(self.arch))
        self.assertTrue(tgt.endswith(os.path.join("Quelle2", "Ordner A", "Vertrag Kopie.docx")))
        # vollstaendiger Originalpfad steckt im Archivpfad (ohne Laufwerks-Doppelpunkt)
        self.assertIn(os.path.splitdrive(dup)[1].strip("\\/"), tgt)
        with open(tgt, "rb") as fh:
            self.assertEqual(fh.read(), self.big)
        self.assertTrue(os.path.isfile(os.path.join(self.src1, "Vertrag.docx")))
        self.assertTrue(os.path.isfile(os.path.join(self.src2, "anders.docx")))
        manifests = os.listdir(os.path.join(self.arch, "_DateiZwilling"))
        self.assertEqual(len(manifests), 1)

    def test_hash_only_mode(self):
        _, _, _, stats = self.archive(verify=False)
        self.assertEqual(stats["done"], 3)

    def test_cross_device_copy(self):
        real = os.rename
        calls = {"n": 0}

        def fake(a, b):
            if b.startswith(self.arch) and not a.endswith(".dzpart"):
                calls["n"] += 1
                raise OSError(errno.EXDEV, "Invalid cross-device link")
            return real(a, b)
        with mock.patch("dateizwilling.archiver.os.rename", side_effect=fake):
            _, _, _, stats = self.archive()
        self.assertGreater(calls["n"], 0)
        self.assertEqual(stats["done"], 3)
        leftovers = [f for _, _, fs_ in os.walk(self.arch) for f in fs_ if f.endswith(".dzpart")]
        self.assertEqual(leftovers, [])

    def test_keeper_changed_after_scan(self):
        sid, groups = self.scan()
        with open(os.path.join(self.src1, "Vertrag.docx"), "r+b") as fh:
            fh.write(b"X")
        arch = Archiver(self.store, Control())
        rid = arch.plan_archive(sid, groups, self.arch)
        stats = arch.execute(rid)
        self.assertEqual(stats["done"], 1)        # nur die kleine Gruppe
        self.assertTrue(os.path.exists(os.path.join(self.src2, "Ordner A", "Vertrag Kopie.docx")))

    def test_keeper_deleted_after_scan(self):
        sid, groups = self.scan()
        os.remove(os.path.join(self.src1, "Vertrag.docx"))
        arch = Archiver(self.store, Control())
        stats = arch.execute(arch.plan_archive(sid, groups, self.arch))
        self.assertTrue(os.path.exists(os.path.join(self.src2, "Ordner A", "Vertrag Kopie.docx")))
        self.assertTrue(os.path.exists(os.path.join(self.src2, "Ordner B", "nochmal.docx")))
        self.assertEqual(stats["skipped"], 2)

    def test_never_overwrites(self):
        dup = os.path.join(self.src2, "Ordner A", "Vertrag Kopie.docx")
        w(archive_target(self.arch, dup), b"alte Archivdatei")
        self.archive()
        with open(archive_target(self.arch, dup), "rb") as fh:
            self.assertEqual(fh.read(), b"alte Archivdatei")
        folder = os.path.dirname(archive_target(self.arch, dup))
        self.assertIn("Vertrag Kopie (DZ2).docx", os.listdir(folder))

    def test_undo(self):
        _, rid, arch, _ = self.archive()
        uid = arch.plan_undo(rid)
        stats = arch.execute(uid)
        self.assertEqual(stats["done"], 3)
        self.assertTrue(os.path.exists(os.path.join(self.src2, "Ordner A", "Vertrag Kopie.docx")))
        self.assertTrue(all(e["state"] == J_UNDONE for e in self.store.journal_entries(rid)))
        left = [f for _, _, fs_ in os.walk(self.arch) for f in fs_ if not f.endswith(".csv")]
        self.assertEqual(left, [])

    def test_purge_requires_keeper(self):
        _, rid, arch, _ = self.archive()
        os.remove(os.path.join(self.src1, "klein.txt"))   # Original der kleinen Gruppe weg
        stats = arch.purge([rid], use_trash=False)
        self.assertEqual(stats["purged"], 2)
        self.assertEqual(stats["kept"], 1)
        self.assertTrue(os.path.exists(archive_target(self.arch, os.path.join(self.src2, "klein-kopie.txt"))))

    def test_cancel_marks_rest_skipped(self):
        sid, groups = self.scan()
        ctl = Control()
        arch = Archiver(self.store, ctl)
        rid = arch.plan_archive(sid, groups, self.arch)
        ctl.cancel()
        with self.assertRaises(Cancelled):
            arch.execute(rid)
        self.assertTrue(all(e["state"] == J_SKIPPED for e in self.store.journal_entries(rid)))


class SafetyTests(Base):
    def test_open_office_document_not_moved(self):
        sid, groups = self.scan()
        w(os.path.join(self.src2, "Ordner A", "~$rtrag Kopie.docx"), b"lock")
        arch = Archiver(self.store, Control())
        stats = arch.execute(arch.plan_archive(sid, groups, self.arch))
        self.assertTrue(os.path.exists(os.path.join(self.src2, "Ordner A", "Vertrag Kopie.docx")))
        self.assertEqual(stats["done"], 2)

    def test_offline_archive_keeps_run_open(self):
        sid, groups = self.scan()
        arch = Archiver(self.store, Control())
        rid = arch.plan_archive(sid, groups, self.arch)
        moved = self.arch + "_offline"
        os.rename(self.arch, moved)                 # USB-Platte "abgezogen"
        notes = recover_all(self.store)
        self.assertTrue(any("nicht erreichbar" in n for n in notes))
        with self.assertRaises(OSError):
            arch.execute(rid)
        self.assertTrue(all(e["state"] == J_PLANNED for e in self.store.journal_entries(rid)))
        os.rename(moved, self.arch)                 # wieder verbunden
        self.assertEqual(Archiver(self.store, Control()).execute(rid)["done"], 3)

    def test_file_changed_between_listing_and_hashing(self):
        ctl = Control()
        sc = Scanner(self.store, ctl)
        real_enum = sc.enumerate

        def enum_then_modify(opts):
            files = real_enum(opts)
            with open(os.path.join(self.src2, "Ordner B", "nochmal.docx"), "ab") as fh:
                fh.write(b"neu")
            return files
        sc.enumerate = enum_then_modify
        _, groups = sc.run(self.opts())
        big = [g for g in groups if g["size"] == 300_000][0]
        self.assertEqual(len(big["members"]), 2)


class CrashTests(Base):
    """Simuliert Abstuerze an kritischen Stellen und prueft die Fortsetzung."""

    def plan(self):
        sid, groups = self.scan()
        arch = Archiver(self.store, Control())
        return arch, arch.plan_archive(sid, groups, self.arch)

    def test_crash_before_any_step(self):
        arch, rid = self.plan()     # geplant, App "stuerzt ab"
        self.assertEqual(len(self.store.runs_unfinished()), 1)
        recover_all(self.store)
        stats = Archiver(self.store, Control()).execute(rid)
        self.assertEqual(stats["done"], 3)

    def test_crash_after_rename_before_journal(self):
        arch, rid = self.plan()
        e = self.store.journal_entries(rid)[0]
        os.makedirs(os.path.dirname(e["dst"]), exist_ok=True)
        os.rename(e["src"], e["dst"])           # Umbenennung erfolgt, Journal nicht
        notes = recover_all(self.store)
        self.assertTrue(any("abgeschlossen" in n for n in notes))
        self.assertEqual(self.store.journal_entries(rid)[0]["state"], J_DONE)
        stats = Archiver(self.store, Control()).execute(rid)
        self.assertEqual(stats["done"], 3)

    def test_crash_during_copy(self):
        arch, rid = self.plan()
        e = self.store.journal_entries(rid)[0]
        tmp = e["dst"] + ".dzpart"
        w(tmp, self.big[:1000])                  # halbe Kopie
        self.store.journal_set(e["id"], "copying", tmp=tmp)
        recover_all(self.store)
        self.assertFalse(os.path.exists(tmp))
        self.assertEqual(self.store.journal_entries(rid)[0]["state"], J_PLANNED)
        stats = Archiver(self.store, Control()).execute(rid)
        self.assertEqual(stats["done"], 3)

    def test_crash_after_copy_before_delete(self):
        arch, rid = self.plan()
        e = [x for x in self.store.journal_entries(rid) if x["size"] == 300_000][0]
        w(e["dst"], self.big)                    # verifizierte Kopie liegt im Archiv
        self.store.journal_set(e["id"], J_COPIED)
        recover_all(self.store)
        self.assertFalse(os.path.exists(e["src"]))
        self.assertEqual([x for x in self.store.journal_entries(rid) if x["id"] == e["id"]][0]["state"], J_DONE)

    def test_crash_with_corrupt_copy_after_copied_state(self):
        arch, rid = self.plan()
        e = [x for x in self.store.journal_entries(rid) if x["size"] == 300_000][0]
        w(e["dst"], self.big2)                   # Ziel defekt
        self.store.journal_set(e["id"], J_COPIED)
        recover_all(self.store)
        self.assertTrue(os.path.exists(e["src"]))  # Quelle NICHT geloescht
        self.assertFalse(os.path.exists(e["dst"]))

    def test_exception_mid_run_then_resume(self):
        sid, groups = self.scan()
        arch = Archiver(self.store, Control())
        rid = arch.plan_archive(sid, groups, self.arch)
        n = {"i": 0}
        real = Archiver._move

        def flaky(self_, *a, **k):
            n["i"] += 1
            if n["i"] == 2:
                raise SystemExit("simulierter Absturz")
            return real(self_, *a, **k)
        with mock.patch.object(Archiver, "_move", flaky):
            with self.assertRaises(SystemExit):
                arch.execute(rid)
        self.assertEqual(self.store.runs_unfinished()[0]["id"], rid)
        stats = Archiver(self.store, Control()).execute(rid)
        self.assertEqual(stats["done"], 3)


class SidecarTests(Base):
    def test_sidecar_moves_and_shared_stem_stays(self):
        raw = os.urandom(200_000)
        a = w(os.path.join(self.src1, "IMG_1.RAF"), raw)
        b = w(os.path.join(self.src2, "Kopie", "IMG_1.RAF"), raw)
        w(b + ".xmp", b"<xmp edit/>")
        w(os.path.join(self.src2, "Kopie", "IMG_1.xmp"), b"<xmp stem/>")
        w(os.path.join(self.src2, "Kopie", "IMG_1.JPG"), os.urandom(5000))  # bleibt -> stem.xmp bleibt
        sid, groups = self.scan()
        arch = Archiver(self.store, Control())
        rid = arch.plan_archive(sid, groups, self.arch)
        arch.execute(rid)
        self.assertTrue(os.path.exists(a))
        self.assertFalse(os.path.exists(b))
        self.assertFalse(os.path.exists(b + ".xmp"))
        self.assertTrue(os.path.exists(archive_target(self.arch, b + ".xmp")))
        self.assertTrue(os.path.exists(os.path.join(self.src2, "Kopie", "IMG_1.xmp")))


class StoreTests(unittest.TestCase):
    def test_corrupt_db_is_replaced(self):
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, "dateizwilling.db"), "wb") as fh:
                fh.write(b"das ist keine datenbank" * 100)
            s = Store(d)
            self.assertEqual(s.cache_count(), 0)
            s.close()
            self.assertTrue(any(".defekt-" in f for f in os.listdir(d)))
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
