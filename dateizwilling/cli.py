"""Kommandozeilenmodus (z. B. fuer geplante Aufgaben).

Beispiele:
  DateiZwilling.exe --cli scan -s D:\\Daten -s E:\\Sicherung -a F:\\DZ-Archiv --report bericht.html
  DateiZwilling.exe --cli scan -s D:\\Daten -a F:\\DZ-Archiv --archive-now --yes
  DateiZwilling.exe --cli resume
  DateiZwilling.exe --cli runs
  DateiZwilling.exe --cli undo --run 3
  DateiZwilling.exe --cli purge --run 3 --yes
  DateiZwilling.exe --cli import F:\\DZ-Archiv
  DateiZwilling.exe --cli restore --run 3 --file "D:\\Daten\\x.docx"
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

from . import APP_COPYRIGHT, APP_NAME, APP_VERSION
from .archiver import Archiver, NeedsAttention, recover_all
from .common import Cancelled, Control, human_size
from .pathutil import KeepAwake
from .report import write_csv, write_html
from .scanner import KEEP_RULES, ScanOptions, Scanner, validate_options
from .state import Store

log = logging.getLogger("dateizwilling.cli")


def _attach_console() -> None:
    """Bei der fensterlosen Windows-EXE die Ausgabe an die aufrufende Konsole haengen."""
    if os.name != "nt" or (sys.stdout and sys.stdout.isatty()):
        return
    try:
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
            sys.stderr = sys.stdout
    except Exception:
        pass


def _printer():
    last = [""]

    def show(d: dict) -> None:
        ph = d.get("phase", "")
        if ph == "enumerate":
            line = f"Suche Dateien … {d.get('files', 0)} Dateien, {d.get('dirs', 0)} Ordner"
        else:
            tot = d.get("total") or 0
            line = f"{ph}: {d.get('files', 0)}/{tot}  {human_size(d.get('bytes', 0))}"
            if d.get("rate"):
                line += f"  {human_size(d['rate'])}/s"
        if line != last[0]:
            last[0] = line
            out = sys.stdout or sys.__stdout__
            if out:
                out.write("\r" + line[:110].ljust(110))
                out.flush()
    return show


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=APP_NAME, description=f"{APP_NAME} {APP_VERSION} – {APP_COPYRIGHT}")
    p.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="Ordner nach Duplikaten durchsuchen")
    s.add_argument("-s", "--source", action="append", required=True, help="Quellordner (mehrfach, Reihenfolge = Prioritaet)")
    s.add_argument("-a", "--archive", required=True, help="Archivordner fuer Duplikate")
    s.add_argument("-p", "--protected", action="append", default=[], help="Geschuetzter Ordner (nie archivieren)")
    s.add_argument("--prefer", action="append", default=[], help="Ordnerregel: bevorzugt als Original")
    s.add_argument("--avoid", action="append", default=[], help="Ordnerregel: nie als Original")
    s.add_argument("-x", "--exclude", action="append", default=[], help="Ausschlussmuster, z. B. *.tmp")
    s.add_argument("--category", action="append", default=[], help="nur Kategorie(n): office, pdf, image, raw, adobe, affinity, captureone, 3d, video, audio, archive, text, other")
    s.add_argument("--keep", choices=KEEP_RULES, default="oldest", help="welche Datei behalten wird")
    s.add_argument("--no-source-order", action="store_true", help="Reihenfolge der Quellordner nicht als Prioritaet nutzen")
    s.add_argument("--workers", type=int, default=0, help="parallele Lesevorgaenge (0 = automatisch)")
    s.add_argument("--min-size", type=int, default=1)
    s.add_argument("--hidden", action="store_true", help="versteckte Dateien einbeziehen")
    s.add_argument("--include-cloud-only", action="store_true", help="Cloud-Platzhalter herunterladen und pruefen")
    s.add_argument("--no-verify", action="store_true", help="kein Byte-Vergleich vor dem Verschieben (nur Pruefsumme)")
    s.add_argument("--no-sidecars", action="store_true", help="Begleitdateien (XMP …) nicht mitverschieben")
    s.add_argument("--report", help="HTML-Bericht schreiben")
    s.add_argument("--report-dir", help="HTML-Bericht mit Datum in diesen Ordner schreiben (Zeitplan)")
    s.add_argument("--anonymize", action="store_true", help="Pfade im Bericht anonymisieren")
    s.add_argument("--similar", action="store_true", help="auch nahezu gleiche Dokumente (gleicher Text)")
    s.add_argument("--no-folders", action="store_true", help="keine doppelten Ordner suchen")
    s.add_argument("--keep-empty-dirs", action="store_true", help="leere Quellordner nicht entfernen")
    s.add_argument("--csv", help="CSV-Bericht schreiben")
    s.add_argument("--archive-now", action="store_true", help="Duplikate direkt archivieren")
    s.add_argument("--yes", action="store_true", help="ohne Rueckfrage")

    sub.add_parser("resume", help="unterbrochene Scans/Laeufe fortsetzen")
    sub.add_parser("runs", help="Laeufe auflisten")
    u = sub.add_parser("undo", help="Archivierung rueckgaengig machen")
    u.add_argument("--run", type=int, help="Lauf-Nummer (Standard: letzter)")
    im = sub.add_parser("import", help="Archiv (CSV-Protokolle) in die Datenbank uebernehmen")
    im.add_argument("archive")
    rs = sub.add_parser("restore", help="einzelne Dateien eines Laufs wiederherstellen")
    rs.add_argument("--run", type=int, required=True)
    rs.add_argument("--file", action="append", required=True, help="Originalpfad (mehrfach)")
    g = sub.add_parser("purge", help="archivierte Duplikate nach Freigabe entfernen")
    g.add_argument("--run", type=int, action="append", required=True)
    g.add_argument("--permanent", action="store_true", help="endgueltig statt Papierkorb")
    g.add_argument("--yes", action="store_true")
    return p


def _confirm(msg: str, yes: bool) -> bool:
    if yes:
        return True
    try:
        return input(msg + " [j/N] ").strip().lower() in ("j", "ja", "y", "yes")
    except EOFError:
        return False


def main(argv: list[str], store: Store) -> int:
    _attach_console()
    args = build_parser().parse_args(argv)
    control = Control()
    with KeepAwake():
        return _run(args, store, control)


def _run(args, store: Store, control: Control) -> int:
    store.maintenance()
    notes = recover_all(store, control)
    for n in notes:
        print("Wiederherstellung:", n)
    try:
        if args.cmd == "scan":
            opts = ScanOptions(
                sources=args.source, archive=args.archive, protected=args.protected,
                prefer=args.prefer, avoid=args.avoid, find_similar=args.similar,
                find_folders=not args.no_folders, remove_empty_dirs=not args.keep_empty_dirs,
                excludes=args.exclude, categories=args.category, min_size=args.min_size,
                include_hidden=args.hidden, skip_cloud_only=not args.include_cloud_only,
                prefer_source_order=not args.no_source_order, keep_rule=args.keep,
                workers=args.workers, verify_bytes=not args.no_verify,
                move_sidecars=not args.no_sidecars)
            errs = validate_options(opts)
            if errs:
                print("Fehler:", ", ".join(errs))
                return 2
            sc = Scanner(store, control, _printer())
            sid, groups = sc.run(opts)
            print()
            st = sc.stats
            print(f"{st['files']} Dateien, {st['groups']} Gruppen, {st['duplicates']} Duplikate, "
                  f"einsparbar {human_size(st['wasted'])}, Fehler {st['errors']}")
            if args.report:
                write_html(args.report, groups, st, anonymize=args.anonymize)
            if args.report_dir:
                import time as _t
                os.makedirs(args.report_dir, exist_ok=True)
                rp = os.path.join(args.report_dir, f"Bericht-{_t.strftime('%Y-%m-%d_%H%M')}.html")
                write_html(rp, groups, st, anonymize=args.anonymize)
                print("Bericht:", rp)
            if args.csv:
                write_csv(args.csv, groups, anonymize=args.anonymize)
            if args.archive_now and groups and _confirm(
                    f"{st['duplicates']} Duplikate nach {opts.archive} verschieben?", args.yes):
                arch = Archiver(store, control, _printer(), verify_bytes=opts.verify_bytes)
                if opts.remove_empty_dirs:
                    arch.empty_dir_roots = list(opts.sources)
                rid = arch.plan_archive(sid, [g for g in groups if g.get("kind", "same") == "same"],
                                        opts.archive, opts.move_sidecars)
                res = arch.execute(rid)
                print(f"\nLauf {rid}: {res}")
            return 0
        if args.cmd == "resume":
            arch = Archiver(store, control, _printer())
            for run in store.runs_unfinished():
                print(f"Setze Lauf {run['id']} ({run['kind']}) fort …")
                print("\n", arch.execute(run["id"]))
            ses = store.session_latest()
            if ses and ses["phase"] == "scanning":
                print(f"Setze Scan (Sitzung {ses['id']}) fort …")
                Scanner(store, control, _printer()).run(ScanOptions.from_dict(ses["options"]), ses["id"])
                print()
            return 0
        if args.cmd == "runs":
            for r in store.runs_list():
                print(f"#{r['id']:>4}  {r['kind']:<8} {r['state']:<10} {r['archive']}  {r['stats']}")
            return 0
        if args.cmd == "undo":
            rid = args.run
            if rid is None:
                runs = [r for r in store.runs_list("archive") if r["state"] in ("done", "cancelled")]
                if not runs:
                    print("Kein Lauf vorhanden.")
                    return 1
                rid = runs[0]["id"]
            arch = Archiver(store, control, _printer())
            uid = arch.plan_undo(rid)
            print("\n", arch.execute(uid))
            return 0
        if args.cmd == "import":
            print(Archiver(store, control).import_archive(args.archive))
            return 0
        if args.cmd == "restore":
            want = {os.path.normcase(os.path.abspath(f)) for f in args.file}
            ids = [e["id"] for e in store.journal_entries(args.run, ("done",))
                   if os.path.normcase(os.path.abspath(e["src"])) in want]
            if not ids:
                print("Keine passenden Dateien in diesem Lauf.")
                return 1
            arch = Archiver(store, control, _printer())
            print("\n", arch.execute(arch.plan_undo(args.run, ids)))
            return 0
        if args.cmd == "purge":
            if not _confirm(f"Archivierte Duplikate der Laeufe {args.run} "
                            f"{'ENDGUELTIG loeschen' if args.permanent else 'in den Papierkorb legen'}?",
                            args.yes):
                return 1
            print(Archiver(store, control).purge(args.run, use_trash=not args.permanent))
            return 0
    except Cancelled:
        print("\nAbgebrochen – Fortsetzen mit: --cli resume")
        return 130
    except NeedsAttention as exc:
        print(f"\nAngehalten: {exc}\nFortsetzen mit: --cli resume")
        return 75
    except KeyboardInterrupt:
        control.cancel()
        print("\nAbgebrochen – Fortsetzen mit: --cli resume")
        return 130
    return 0
