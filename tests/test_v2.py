"""Tests fuer die Neuerungen von Version 2.0."""
from __future__ import annotations

import base64
import io
import os
import shutil
import struct
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dateizwilling import archiver as archmod  # noqa: E402
from dateizwilling import pathutil, scheduler  # noqa: E402
from dateizwilling.archiver import Archiver, NeedsAttention  # noqa: E402
from dateizwilling.common import Control  # noqa: E402
from dateizwilling.content import text_fingerprint  # noqa: E402
from dateizwilling.formats import category_of  # noqa: E402
from dateizwilling.pathutil import archive_target  # noqa: E402
from dateizwilling.preview import make_preview  # noqa: E402
from dateizwilling.report import category_stats, write_csv, write_html  # noqa: E402
from dateizwilling.scanner import ScanOptions, Scanner, choose_keepers  # noqa: E402
from dateizwilling.state import J_DONE, J_PLANNED, J_UNDONE, ScanTemp, Store  # noqa: E402


def w(path: str, data: bytes, mtime: float | None = None) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    if mtime:
        os.utime(path, (mtime, mtime))
    return path


def docx(path: str, text: str, author: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="x"><w:body><w:p><w:t>{text}</w:t></w:p>'
                                        f'</w:body></w:document>')
        z.writestr("docProps/core.xml", f"<cp><creator>{author}</creator></cp>")
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dz2_")
        self.a = os.path.join(self.tmp, "A")
        self.b = os.path.join(self.tmp, "B")
        self.arch = os.path.join(self.tmp, "Archiv")
        self.store = Store(os.path.join(self.tmp, "daten"))
        self.data = os.urandom(200_000)
        w(os.path.join(self.a, "orig.bin"), self.data, 1_600_000_000)
        w(os.path.join(self.b, "kopie.bin"), self.data, 1_700_000_000)

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def opts(self, **kw):
        base = dict(sources=[self.a, self.b], archive=self.arch, workers=2)
        base.update(kw)
        return ScanOptions(**base)

    def scan(self, **kw):
        sc = Scanner(self.store, Control())
        sid, groups = sc.run(self.opts(**kw))
        self.scanner = sc
        return sid, groups

    def archive_all(self, arch=None, **kw):
        sid, groups = self.scan(**kw)
        arch = arch or Archiver(self.store, Control())
        rid = arch.plan_archive(sid, [g for g in groups if g.get("kind", "same") == "same"], self.arch)
        return sid, rid, arch, arch.execute(rid)


class SafetyV2(Base):
    def test_s1_purge_compares_bytes(self):
        _, rid, arch, _ = self.archive_all()
        # Original gleich gross, aber inhaltlich geaendert -> Archivkopie ist letzte alte Fassung
        with open(os.path.join(self.a, "orig.bin"), "r+b") as fh:
            fh.write(b"XYZ")
        stats = arch.purge([rid], use_trash=False)
        self.assertEqual(stats["purged"], 0)
        self.assertEqual(stats["kept"], 1)
        self.assertTrue(os.path.exists(archive_target(self.arch, os.path.join(self.b, "kopie.bin"))))

    def test_s2_not_enough_space_pauses_run(self):
        sid, groups = self.scan()
        arch = Archiver(self.store, Control())
        rid = arch.plan_archive(sid, groups, self.arch)
        with mock.patch.object(archmod, "same_device", return_value=False), \
                mock.patch.object(archmod, "disk_free", return_value=10):
            with self.assertRaises(NeedsAttention):
                arch.execute(rid)
        self.assertEqual(self.store.runs_unfinished()[0]["id"], rid)
        self.assertTrue(all(e["state"] == J_PLANNED for e in self.store.journal_entries(rid)))
        self.assertEqual(Archiver(self.store, Control()).execute(rid)["done"], 1)

    def test_s3_fat32_limit(self):
        sid, groups = self.scan()
        arch = Archiver(self.store, Control())
        rid = arch.plan_archive(sid, groups, self.arch)
        with mock.patch.object(archmod, "FAT32_MAX", 1000), \
                mock.patch.object(archmod, "same_device", return_value=False), \
                mock.patch.object(archmod, "fs_type", return_value="fat32"):
            stats = arch.execute(rid)
        self.assertEqual(stats["skipped"], 1)
        self.assertTrue(os.path.exists(os.path.join(self.b, "kopie.bin")))

    @unittest.skipIf(os.name == "nt", "Windows erlaubt ':' und '?' in Dateinamen ohnehin nicht")
    def test_s3_safe_names(self):
        w(os.path.join(self.b, "Bericht: Q1?.bin"), self.data)
        with mock.patch.object(archmod, "needs_safe_names", return_value=True):
            _, rid, arch, stats = self.archive_all()
        self.assertEqual(stats["done"], 2)
        names = [f for _, _, fs_ in os.walk(self.arch) for f in fs_]
        self.assertIn("Bericht_ Q1_.bin", names)
        arch.execute(arch.plan_undo(rid))
        self.assertTrue(os.path.exists(os.path.join(self.b, "Bericht: Q1?.bin")))

    def test_s4_import_archive_into_new_database(self):
        self.archive_all()
        fresh = Store(os.path.join(self.tmp, "neue-daten"))
        try:
            res = Archiver(fresh, Control()).import_archive(self.arch)
            self.assertEqual(res["files"], 1)
            self.assertEqual(Archiver(fresh, Control()).import_archive(self.arch)["files"], 0)  # keine Doppel
            run = fresh.runs_list("archive")[0]
            arch = Archiver(fresh, Control())
            arch.execute(arch.plan_undo(run["id"]))
            self.assertTrue(os.path.exists(os.path.join(self.b, "kopie.bin")))
        finally:
            fresh.close()

    def test_s5_restore_single_file(self):
        w(os.path.join(self.b, "zweite.bin"), self.data)
        _, rid, arch, stats = self.archive_all()
        self.assertEqual(stats["done"], 2)
        e = [x for x in self.store.journal_entries(rid) if x["src"].endswith("zweite.bin")][0]
        arch.execute(arch.plan_undo(rid, [e["id"]]))
        self.assertTrue(os.path.exists(os.path.join(self.b, "zweite.bin")))
        self.assertFalse(os.path.exists(os.path.join(self.b, "kopie.bin")))
        states = {x["src"].rsplit(os.sep, 1)[-1]: x["state"] for x in self.store.journal_entries(rid)}
        self.assertEqual(states, {"zweite.bin": J_UNDONE, "kopie.bin": J_DONE})

    def test_st2_waits_for_drive(self):
        sid, groups = self.scan()
        phases = []
        arch = Archiver(self.store, Control(), lambda d: phases.append(d.get("phase")))
        rid = arch.plan_archive(sid, groups, self.arch)
        calls = {"n": 0}
        real = archmod.is_reachable

        def flaky(p):
            calls["n"] += 1
            return real(p) if calls["n"] > 3 else False
        with mock.patch.object(archmod, "is_reachable", side_effect=flaky):
            stats = arch.execute(rid)
        self.assertEqual(stats["done"], 1)
        self.assertIn("waiting", phases)

    def test_st2_cancel_while_waiting(self):
        sid, groups = self.scan()
        ctl = Control()
        arch = Archiver(self.store, ctl)
        rid = arch.plan_archive(sid, groups, self.arch)
        threading.Timer(0.6, ctl.cancel).start()
        with mock.patch.object(archmod, "is_reachable", return_value=False):
            with self.assertRaises(Exception):
                arch.execute(rid)
        self.assertTrue(os.path.exists(os.path.join(self.b, "kopie.bin")))

    def test_empty_dirs_removed_but_not_roots(self):
        w(os.path.join(self.b, "tief", "unter", "kopie2.bin"), self.data)
        arch = Archiver(self.store, Control())
        arch.empty_dir_roots = [self.a, self.b]
        self.archive_all(arch)
        self.assertFalse(os.path.exists(os.path.join(self.b, "tief")))
        self.assertTrue(os.path.isdir(self.b))

    def test_cloud_and_risky_detection(self):
        self.assertEqual(pathutil.cloud_sync_kind("/home/x/Nextcloud/Archiv"), "Nextcloud")
        self.assertEqual(pathutil.cloud_sync_kind("/Users/x/Library/CloudStorage/OneDrive/A"), "OneDrive")
        self.assertEqual(pathutil.cloud_sync_kind("/Users/x/Library/CloudStorage/Box-x/A"), "Cloud")
        self.assertIsNone(pathutil.cloud_sync_kind(self.tmp))
        self.assertEqual(pathutil.risky_source("/"), "root")
        self.assertEqual(pathutil.risky_source(os.path.expanduser("~")), "home")
        # normaler Datenordner -> keine Warnung (bewusst ausserhalb von AppData/Temp,
        # denn unter Windows liegen Testordner in %LOCALAPPDATA%\\Temp = Programmdaten)
        data_dir = r"D:\Daten\Projekte" if os.name == "nt" else "/Volumes/Daten/Projekte"
        self.assertIsNone(pathutil.risky_source(data_dir))
        if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
            self.assertEqual(pathutil.risky_source(os.path.join(os.environ["LOCALAPPDATA"], "x")), "system")

    def test_keep_awake_and_anonymize(self):
        with pathutil.KeepAwake():
            pass
        home = os.path.expanduser("~")
        self.assertTrue(pathutil.anonymize_path(os.path.join(home, "Dokumente", "x.pdf")).startswith("~"))


class FeaturesV2(Base):
    def test_f2_duplicate_folders(self):
        for root in (self.a, self.b):
            for i in range(3):
                w(os.path.join(root, "Projekt", "sub", f"f{i}.dat"), bytes([i]) * 5000)
            w(os.path.join(root, "Projekt", "readme.txt"), b"gleicher Inhalt fuer beide Projekte")
        w(os.path.join(self.b, "Anders", "f0.dat"), bytes([0]) * 5000)
        w(os.path.join(self.b, "Anders", "extra.dat"), b"nur hier")
        self.scan()
        fgs = self.scanner.folder_groups
        paths = sorted(f["path"] for fg in fgs for f in fg["folders"])
        self.assertIn(os.path.join(self.a, "Projekt"), paths)
        self.assertIn(os.path.join(self.b, "Projekt"), paths)
        self.assertNotIn(os.path.join(self.a, "Projekt", "sub"), paths)   # nur oberste Ordner
        self.assertFalse(any("Anders" in p for p in paths))
        loaded = self.store.folders_load(self.store.session_latest()["id"])
        self.assertEqual(len(loaded), len(fgs))
        self.assertEqual(sum(1 for fg in loaded for f in fg["folders"] if f["keep"]), len(loaded))

    def test_f3_folder_rules(self):
        opts = self.opts(prefer=[self.b])
        members = [{"path": os.path.join(self.a, "x"), "mtime_ns": 1}, {"path": os.path.join(self.b, "x"), "mtime_ns": 2}]
        choose_keepers(members, opts)
        self.assertTrue(members[1]["keep"])
        opts = self.opts(avoid=[self.a])
        choose_keepers(members, opts)
        self.assertTrue(members[1]["keep"])
        opts = self.opts(avoid=[self.a, self.b])  # alle "nie Original" -> trotzdem genau eines
        choose_keepers(members, opts)
        self.assertEqual(sum(m["keep"] for m in members), 1)

    def test_f8_similar_documents(self):
        text = "Angebot fuer die Antennenanlage DM5CQ mit allen Positionen und Preisen"
        d1 = docx(os.path.join(self.a, "Angebot.docx"), text, "Stefan")
        d2 = docx(os.path.join(self.b, "Angebot (gespeichert).docx"), text, "Stefan J. Kaiser")
        docx(os.path.join(self.b, "Anderes.docx"), text + " plus Nachtrag", "Stefan")
        self.assertEqual(text_fingerprint(d1), text_fingerprint(d2))
        sid, groups = self.scan(find_similar=True)
        sim = [g for g in groups if g["kind"] == "similar"]
        self.assertEqual(len(sim), 1)
        self.assertEqual(len(sim[0]["members"]), 2)
        arch = Archiver(self.store, Control())
        rid = arch.plan_archive(sid, sim, self.arch)
        stats = arch.execute(rid)
        self.assertEqual(stats["done"], 1)
        self.assertEqual(len(self.store.dupes_load(sid)), len(groups))

    def test_3d_category_and_previews(self):
        self.assertEqual(category_of("halter.stl"), "3d")
        self.assertEqual(category_of("druck.3mf"), "3d")
        self.assertEqual(category_of("teil.step"), "3d")
        self.assertEqual(category_of("benchy.gcode"), "3d")
        tris = [((0, 0, 0), (10, 0, 0), (0, 10, 0)), ((0, 0, 0), (0, 10, 0), (0, 0, 10)),
                ((0, 0, 0), (10, 0, 0), (0, 0, 10)), ((10, 0, 0), (0, 10, 0), (0, 0, 10))]
        stl = os.path.join(self.tmp, "t.stl")
        with open(stl, "wb") as fh:
            fh.write(b"\0" * 80 + struct.pack("<I", len(tris)))
            for t in tris:
                fh.write(struct.pack("<12fH", 0, 0, 0, *t[0], *t[1], *t[2], 0))
        self.assertIsNotNone(make_preview(stl))
        from PIL import Image
        bio = io.BytesIO()
        Image.new("RGB", (64, 48), (0, 200, 0)).save(bio, "PNG")
        b64 = base64.b64encode(bio.getvalue()).decode()
        gc = os.path.join(self.tmp, "p.gcode")
        with open(gc, "w") as fh:
            fh.write(f"; thumbnail begin 64x48 {len(b64)}\n; {b64}\n; thumbnail end\nG28\n")
        self.assertEqual(make_preview(gc).size, (64, 48))
        jb = io.BytesIO()
        Image.new("RGB", (320, 200), (200, 0, 0)).save(jb, "JPEG")
        raw = w(os.path.join(self.tmp, "x.nef"), os.urandom(3000) + jb.getvalue() + os.urandom(1000))
        self.assertIsNotNone(make_preview(raw))

    def test_f6_stats_and_anonymized_report(self):
        sid, groups = self.scan()
        cats = category_stats(groups)
        self.assertEqual(cats[0]["duplicates"], 1)
        home = os.path.expanduser("~")
        groups[0]["members"][0]["path"] = os.path.join(home, "geheim", "x.bin")
        h = os.path.join(self.tmp, "r.html")
        c = os.path.join(self.tmp, "r.csv")
        write_html(h, groups, {}, "de", anonymize=True)
        write_csv(c, groups, anonymize=True)
        for p in (h, c):
            with open(p, encoding="utf-8-sig") as fh:
                self.assertNotIn(home, fh.read())

    def test_f7_scheduler_command(self):
        cmd = scheduler.scan_command([self.a, self.b], self.arch)
        self.assertIn("--cli", cmd)
        self.assertIn("--report-dir", cmd)
        self.assertNotIn("--archive-now", cmd)   # Zeitplan verschiebt nie etwas
        if os.name != "nt" and sys.platform != "darwin":
            ok, _ = scheduler.create(self.tmp, [self.a], self.arch, True, 0, "19:42")
            self.assertFalse(ok)

    def test_st4_scan_temp_and_maintenance(self):
        t = ScanTemp(os.path.join(self.tmp, "daten"), 99)
        for i in range(10):
            t.add(f"k{i}", os.path.join(self.a, "d", f"f{i}"), i % 3, 1)
        self.assertEqual(t.total(), 10)
        sizes = [g[0][1] for g in t.candidates()]
        self.assertEqual(sorted(sizes), [0, 1, 2])
        self.assertEqual(t.dir_counts()[os.path.join(self.a, "d")][0], 10)
        t.close()
        self.assertFalse(os.path.exists(t.path))
        self.assertTrue(self.store.maintenance(force=True))
        dest = os.path.join(self.tmp, "sicherung", "db.sqlite")
        self.assertTrue(self.store.backup_to(dest))
        self.assertGreater(os.path.getsize(dest), 0)

    def test_auto_workers(self):
        n = pathutil.auto_workers([self.a])
        self.assertIn(n, (1, 2, 4))
        sid, _ = self.scan(workers=0)
        self.assertIn(self.store.session_get(sid)["stats"]["workers"], (1, 2, 4))


if __name__ == "__main__":
    unittest.main()
