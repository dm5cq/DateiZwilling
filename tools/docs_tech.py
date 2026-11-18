import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from pdfkit_dz import build  # noqa: E402

ROOT = sys.argv[1]
ICON = os.path.join(ROOT, "assets", "icon.png")
OUT = os.path.join(ROOT, "docs")
PDF = os.path.join(ROOT, "Dokumentation")
os.makedirs(PDF, exist_ok=True)
FOOT_DE = "© 2026 Stefan J. Kaiser DM5CQ / OE8KKS · Idee und Konzept · Umsetzung: Claude (Anthropic), 18.11.2026"
FOOT_EN = "© 2026 Stefan J. Kaiser DM5CQ / OE8KKS · Idea and concept · Implementation: Claude (Anthropic), 18.11.2026"

prompt = open(os.path.join(OUT, "PROMPT.md"), encoding="utf-8").read()
MSG1 = prompt.split("## Nachricht 1")[1].split("## Nachricht 2")[0].strip().lstrip("> ").strip()
MSG2 = prompt.split("## Nachricht 2")[1].split("---")[0].strip().lstrip("> ").strip()
N_TESTS = sys.argv[2]
MSG3 = prompt.split("## Nachtrag 1.0.1")[1].strip().lstrip("> ").strip()

STATE = ("planned ──rename (gleiches Laufwerk)──────────────────────► done\n"
         "   │\n"
         "   └─ anderes Laufwerk ─► copying ─ verifiziert ─► copied ─ Quelle entfernt ─► done\n"
         "                             │                        │\n"
         "               Absturz: *.dzpart löschen     Absturz: Ziel-Prüfsumme prüfen,\n"
         "               → zurück auf planned          Quelle entfernen → done")
STATE_EN = STATE.replace("gleiches Laufwerk", "same drive").replace("anderes Laufwerk", "other drive") \
    .replace("verifiziert", "verified").replace("Quelle entfernt", "source removed") \
    .replace("Absturz: *.dzpart löschen", "crash: delete *.dzpart  ").replace("Absturz: Ziel-Prüfsumme prüfen,", "crash: verify target checksum, ") \
    .replace("→ zurück auf planned", "→ back to planned   ").replace("Quelle entfernen → done", "remove source → done")

MODULES_DE = [
    ["DateiZwilling.py", "Startpunkt: Datenordner, Protokolle (rotierend), Absturzprotokoll (faulthandler), Einzelinstanz-Sperre, Auswahl GUI/CLI"],
    ["dateizwilling/scanner.py", "Scan-Engine: Verzeichnislauf, Größengruppen, Hardlink-Erkennung, Schnell-/Voll-Prüfsumme (parallel), Gruppenbildung, Wahl des Originals"],
    ["dateizwilling/archiver.py", "Planung, Ausführung, Verifikation, Absturz-Wiederherstellung, Rückgängig, Bereinigen, CSV-Manifest"],
    ["dateizwilling/state.py", "SQLite-Datenbank (WAL, synchronous=FULL): Prüfsummen-Cache, Sitzungen, Duplikate, Läufe, Journal"],
    ["dateizwilling/pathutil.py", "Lange Windows-Pfade (\\\\?\\), Archivpfad-Abbildung, Cloud-Platzhalter, Netzlaufwerk-Erkennung, Papierkorb, Datenordner, Sperre"],
    ["dateizwilling/formats.py", "Kategorien, Ausschluss- und Schutzregeln, Begleitdateien, Erkennung geöffneter Office-Dokumente"],
    ["dateizwilling/common.py", "Pause/Abbruch (Control), BLAKE2b, Byte-Vergleich, Formatierung, CSV-Schutz"],
    ["dateizwilling/gui.py", "Tkinter-Oberfläche im BildZwilling-Stil, Hintergrund-Thread + Nachrichten-Warteschlange"],
    ["dateizwilling/cli.py", "Kommandozeile: scan, resume, runs, undo, purge"],
    ["dateizwilling/report.py", "HTML- und CSV-Bericht"],
    ["dateizwilling/i18n.py / config.py", "Texte DE/EN, Einstellungen (atomar gespeichert)"],
]
MODULES_EN = [
    ["DateiZwilling.py", "Entry point: data folder, rotating logs, crash log (faulthandler), single-instance lock, GUI/CLI selection"],
    ["dateizwilling/scanner.py", "Scan engine: directory walk, size groups, hardlink detection, quick/full checksum (parallel), grouping, choice of original"],
    ["dateizwilling/archiver.py", "Planning, execution, verification, crash recovery, undo, clean-up, CSV manifest"],
    ["dateizwilling/state.py", "SQLite database (WAL, synchronous=FULL): checksum cache, sessions, duplicates, runs, journal"],
    ["dateizwilling/pathutil.py", "Long Windows paths (\\\\?\\), archive path mapping, cloud placeholders, network drive detection, recycle bin, data folder, lock"],
    ["dateizwilling/formats.py", "Categories, exclusion and protection rules, sidecar files, detection of open Office documents"],
    ["dateizwilling/common.py", "Pause/cancel (Control), BLAKE2b, byte comparison, formatting, CSV protection"],
    ["dateizwilling/gui.py", "Tkinter interface in BildZwilling style, background thread + message queue"],
    ["dateizwilling/cli.py", "Command line: scan, resume, runs, undo, purge"],
    ["dateizwilling/report.py", "HTML and CSV report"],
    ["dateizwilling/i18n.py / config.py", "Texts DE/EN, settings (saved atomically)"],
]

REVIEW_DE = [
    ["R1", "Zeitstempel aus Verzeichniseinträgen weichen auf Netzlaufwerken von os.stat ab", "Werte aus os.stat für alle Kandidaten"],
    ["R2", "Archivlaufwerk beim Neustart nicht verbunden", "Wiederherstellung/Fortsetzen warten, bis das Archiv erreichbar ist"],
    ["R3", "Geöffnete Office-Dokumente könnten verschoben werden", "Sperrdateien ~$… / .~lock.…# → übersprungen"],
    ["R4", "Schnell-/Voll-Prüfsumme im Cache vermischbar", "Getrennte Behandlung kleiner/großer Dateien"],
    ["R5", "CSV-/Formel-Injektion in Excel", "csv_safe() für Bericht und Manifest"],
    ["R6", "SQLite-Verbindungsleck bei defekter DB", "Verbindung schließen, DB sichern und neu anlegen"],
    ["R7", "Emoji außerhalb BMP in Tk 8.6", "durch BMP-Symbole ersetzt"],
    ["R8", "Speicherbedarf bei Millionen Dateien", "__slots__ für Dateieinträge"],
    ["R9", "Archiv-Fortschritt > 100 %", "Fortschritt nach Dateien"],
    ["R10", "1.0.1: Native Windows-Meldungsfenster weiß", "Eigene dunkle Dialoge; Test verbietet native Meldungsfenster"],
    ["R11", "1.0.1: Titelleiste des Info-Dialogs weiß", "DWM über Rahmenfenster, erneut nach Anzeigen + Neuzeichnen"],
    ["R12", "1.0.1: Scan-Knopf erst im Vollbild sichtbar", "Fenster an Bildschirm angepasst, Knöpfe fest unten, Seitenleiste scrollbar"],
    ["R13", "1.0.1: Weiße Checkboxen", "Indikatorfarben grau / orange mit weißem Haken"],
]
REVIEW_EN = [
    ["R1", "Directory-entry timestamps differ from os.stat on network drives", "os.stat values for all candidates"],
    ["R2", "Archive drive not connected at restart", "Recovery/resume wait until the archive is reachable"],
    ["R3", "Open Office documents could be moved", "Lock files ~$… / .~lock.…# → skipped"],
    ["R4", "Quick/full checksum could be mixed in cache", "Separate handling of small/large files"],
    ["R5", "CSV/formula injection in Excel", "csv_safe() for report and manifest"],
    ["R6", "SQLite connection leak on corrupt DB", "Close connection, back up DB and recreate"],
    ["R7", "Non-BMP emoji in Tk 8.6", "Replaced with BMP symbols"],
    ["R8", "Memory use with millions of files", "__slots__ for file records"],
    ["R9", "Archive progress > 100 %", "Progress by files"],
    ["R10", "1.0.1: native Windows message boxes white", "Own dark dialogs; test forbids native message boxes"],
    ["R11", "1.0.1: About dialog title bar white", "DWM via frame window, re-applied after mapping + redraw"],
    ["R12", "1.0.1: scan button only visible when maximized", "Window fitted to screen, buttons anchored at bottom, scrollable sidebar"],
    ["R13", "1.0.1: white check boxes", "Indicator colours grey / orange with white tick"],
]

de = [
    ("h1", "1  Überblick"),
    ("p", "DateiZwilling ist ein Bereinigungswerkzeug für vergessene, inhaltsgleiche Dateien. Es vergleicht den <b>Inhalt</b> (nicht den Namen) beliebiger Dateien in mehreren Quellordnern und verschiebt Duplikate in ein Archiv, das die Originalpfade exakt abbildet. Endgültig entfernt wird erst nach ausdrücklicher Freigabe. Die App ist in Python 3 geschrieben, nutzt für Logik und Datenhaltung ausschließlich die Standardbibliothek (sqlite3, hashlib, tkinter) und wird mit PyInstaller als portable Windows-EXE bzw. macOS-App ausgeliefert. Pillow ist optional (Bildvorschau)."),
    ("table", ["Ziel", "Umsetzung"], [
        ["Zuverlässigkeit", "Mehrstufiger Inhaltsvergleich, Byte-für-Byte-Prüfung vor jeder Verschiebung"],
        ["Keine Datenverluste", "Verschieben statt Löschen, Verifikation, nie überschreiben, Freigabe vor dem Entfernen"],
        ["Ausfallsicherheit", "Write-Ahead-Journal, Prüfsummen-Cache, automatische Reparatur und Fortsetzen"],
        ["Nachvollziehbarkeit", "Exakte Pfadabbildung, CSV-Manifest je Lauf im Archiv, Protokolldateien, HTML-Bericht"],
        ["Portabilität", "Onefile-EXE, Daten neben der EXE; macOS-Build-Skript"],
    ], [0.25, 0.75]),
    ("h1", "2  Architektur"),
    ("table", ["Modul", "Aufgabe"], MODULES_DE, [0.32, 0.68]),
    ("p", "Die Oberfläche läuft im Haupt-Thread. Scan, Archivierung, Rückgängig und Bereinigen laufen in einem Hintergrund-Thread und melden Fortschritt, Protokollzeilen und Ergebnisse über eine Warteschlange, die die Oberfläche alle 100 ms abfragt. Pause und Abbruch werden über ein threadsicheres <i>Control</i>-Objekt an Prüfpunkten (alle 8 MiB bzw. zwischen Dateien) umgesetzt."),
    ("h1", "3  Erkennungsverfahren"),
    ("ol", [
        "<b>Verzeichnislauf</b> (os.scandir, iterativ): ohne Symlinks/Junctions, ohne Archiv, System-, Papierkorb- und Paketordner, optional ohne versteckte Dateien, Cloud-Platzhalter (Windows-Attribute OFFLINE/RECALL_ON_*, macOS SF_DATALESS), Programm-Kataloge, Ausschlussmuster und Kategorien. Verschachtelte Quellordner werden zusammengeführt.",
        "<b>Größengruppen</b>: nur gleich große Dateien kommen weiter. Für Kandidaten werden Größe/Zeit per os.stat neu gelesen; Hardlinks (gleiches Gerät + Inode) gelten als eine Datei.",
        "<b>Schnell-Prüfsumme</b>: BLAKE2b-160 über Größe + erste und letzte 64 KiB. Dateien bis 128 KiB erhalten direkt die volle Prüfsumme.",
        "<b>Volle Prüfsumme</b>: BLAKE2b-256 in 1-MiB-Blöcken, parallel (1–16 Threads). Ändert sich eine Datei während des Lesens (Größe/Zeit vor und nach), wird sie verworfen.",
        "<b>Gruppen</b> nach (Größe, Prüfsumme). <b>Original</b>: Dateien in geschützten Ordnern bleiben immer; sonst Priorität der Quellordner, dann Regel (älteste/neueste/kürzester/längster Pfad), dann Pfadname.",
        "<b>Vor dem Verschieben</b>: erneuter Byte-für-Byte-Vergleich mit dem behaltenen Original (abschaltbar → dann erneute Prüfsumme).",
    ]),
    ("h1", "4  Archivierung und Pfadabbildung"),
    ("code", "Windows  D:\\Ordner\\Datei.ext            → <Archiv>\\D\\Ordner\\Datei.ext\n"
             "UNC      \\\\Server\\Freigabe\\Ordner\\X    → <Archiv>\\UNC\\Server\\Freigabe\\Ordner\\X\n"
             "macOS    /Volumes/HDD/Ordner/X           → <Archiv>/Volumes/HDD/Ordner/X\n"
             "belegt   …\\Datei.ext                     → …\\Datei (DZ2).ext   (nie überschreiben)"),
    ("p", "Der gesamte Plan eines Laufs (inkl. Begleitdateien) wird in <b>einer</b> Transaktion ins Journal geschrieben. Gleiches Laufwerk: atomares <i>rename</i> + fsync des Ordners. Anderes Laufwerk: Kopie nach <i>Ziel.dzpart</i> mit gleichzeitiger Prüfsumme, fsync, Rücklesen und Vergleich, Übernahme der Zeitstempel, Umbenennen in den Zielnamen, erst dann Entfernen der Quelle. Lässt sich die Quelle nicht entfernen (gesperrt), wird die Kopie wieder entfernt. Je Lauf entsteht im Archiv <i>_DateiZwilling/Archivierung-Lauf-NNNNN.csv</i> (Zeitpunkt, Status, Originalpfad, Archivpfad, Original, Größe, Prüfsumme)."),
    ("h2", "Begleitdateien"),
    ("p", "<i>name.ext.xmp/.pp3/.dop/.on1</i>, <i>name.xmp/.aae/.thm</i> und Capture One <i>CaptureOne/Settings*/name.ext.cos</i> werden mit dem Duplikat verschoben – aber nur, wenn das Duplikat selbst erfolgreich verschoben wurde und eine stammgleiche XMP nicht noch zu einer bleibenden Datei (RAW+JPEG) gehört."),
    ("h1", "5  Ausfallsicherheit"),
    ("code", STATE),
    ("ul", [
        "Jeder Zustandswechsel wird <b>vor</b> der Aktion in SQLite (WAL, synchronous=FULL) festgeschrieben.",
        "Beim Start repariert <i>recover_all()</i> alle offenen Läufe: erfolgtes Umbenennen wird erkannt (Ziel vorhanden, Prüfsumme passt), halbe Kopien werden gelöscht, verifizierte Kopien abgeschlossen. Danach wird angeboten, den Lauf an der Abbruchstelle fortzusetzen.",
        "Ist das Archivlaufwerk nicht erreichbar, wird nichts verändert; der Lauf bleibt offen.",
        "Scan: Prüfsummen werden laufend (≤ 2 s / 300 Dateien) in den Cache geschrieben (Schlüssel: Pfad + Größe + Änderungszeit). Ein unterbrochener Scan wird fortgesetzt, ohne bereits geprüfte Dateien erneut zu lesen.",
        "Beenden während eines Laufs: Scan wird sauber abgebrochen (Cache gesichert); Archivierung wird pausiert und beim nächsten Start fortgesetzt.",
        "Beschädigte Datenbank: Selbstprüfung (quick_check), Sicherung als <i>.defekt-Datum</i>, Neuanlage. Das CSV-Manifest im Archiv bleibt als unabhängiger Nachweis.",
        "Absturzprotokoll über faulthandler, unbehandelte Ausnahmen (auch in Threads) werden protokolliert.",
    ]),
    ("h1", "6  Datenhaltung"),
    ("table", ["Ort / Tabelle", "Inhalt"], [
        ["DateiZwilling-Daten\\ (neben der EXE)", "Portabler Datenordner; ohne Schreibrecht: %LOCALAPPDATA%\\DateiZwilling bzw. ~/Library/Application Support/DateiZwilling"],
        ["dateizwilling.db: hash_cache", "Pfad, Größe, Änderungszeit, Schnell-/Voll-Prüfsumme (Einträge > 1 Jahr unbenutzt werden entfernt)"],
        ["sessions / dupes", "Scan-Sitzungen (Quellen, Archiv, Optionen, Phase, Statistik) und Duplikatgruppen inkl. Auswahl"],
        ["runs / journal", "Archivierungs-, Rückgängig-Läufe und jeder einzelne Schritt mit Zustand"],
        ["einstellungen.json", "Oberflächen- und Prüfeinstellungen (atomar geschrieben)"],
        ["Protokolle\\", "dateizwilling.log (5 × 5 MB rotierend), absturz.log"],
    ], [0.35, 0.65]),
    ("h1", "7  Dateiformate und Schutzregeln"),
    ("p", "Da der Inhalt verglichen wird, wird jedes Format unterstützt. Kategorien: Office (Word, Excel, PowerPoint, Access, Publisher, Visio, OneNote, Project, Outlook-Dateien, LibreOffice, iWork, WPS), PDF/E-Books, Bilder (inkl. FITS/XISF für Seestar), Kamera-RAW (Fujifilm, Nikon, Canon, Panasonic, OM System, Leica, Hasselblad, Sony, Pentax, Sigma, DJI, Insta360, GoPro …), Adobe, Affinity (inkl. .af), Capture One, Video, Audio, Archive, Text/Code, Sonstige."),
    ("table", ["Regel", "Beispiele"], [
        ["Nie gescannt (Systemdateien)", "~$*, .~lock.*#, Thumbs.db, desktop.ini, .DS_Store, ._*, *.lnk, *.dzpart, pagefile.sys"],
        ["Nie betreten (Ordner)", "$Recycle.Bin, System Volume Information, Windows, Program Files, .Trashes, .git, node_modules, @eaDir, #recycle, _DateiZwilling"],
        ["Geschützte Pakete", ".app, .photoslibrary, .lrdata, .lrlibrary, .cocatalog, .fcpbundle, .logicx, .imovielibrary, .affinitycatalog …"],
        ["Geschützte Kataloge (Option)", ".lrcat, .cocatalogdb, .cosessiondb, .pst, .ost, SQLite-WAL/SHM"],
        ["Weitere", "Symlinks/Junctions, Hardlinks, Cloud-Platzhalter, geöffnete Office-Dokumente, geschützte Ordner"],
    ], [0.3, 0.7]),
    ("h1", "8  Kommandozeile"),
    ("code", "DateiZwilling.exe --cli scan -s D:\\Daten -s E:\\Sicherung -a F:\\DZ-Archiv\n"
             "        [-p geschützt] [-x *.tmp] [--category office --category pdf]\n"
             "        [--keep oldest|newest|shortest|longest] [--workers 2] [--no-verify]\n"
             "        [--report bericht.html] [--csv bericht.csv] [--archive-now --yes]\n"
             "DateiZwilling.exe --cli resume | runs | undo [--run N] | purge --run N [--permanent] --yes"),
    ("h1", "9  Build und Verteilung"),
    ("ul", [
        "<b>Windows:</b> <i>build-exe.bat</i> – prüft Python ≥ 3.10 und tkinter, legt .venv an, installiert Pillow + PyInstaller, führt alle Tests aus und erzeugt <i>dist\\DateiZwilling.exe</i> (onefile, windowed, Icon, Versionsinfo).",
        "<b>macOS:</b> <i>build-macos.sh</i> – .app mit Bundle-ID, Ad-hoc-Signatur und DMG.",
        "Code-Signatur (optional) verhindert SmartScreen-/Gatekeeper-Hinweise.",
    ]),
    ("h1", "10  Tests"),
    ("p", f"{N_TESTS} automatische Tests (<i>python -m unittest discover -s tests</i>) decken Scan, Archivierung, Pfadabbildung, Laufwerkswechsel, Rückgängig, Bereinigen, Schutzregeln, Datenbankdefekt, sechs Absturz-Szenarien und einen kompletten Oberflächen-Ablauf (mit Tk-Attrappe) ab. Zusätzlich: Praxistest mit <i>kill -9</i> während einer Kopie auf ein anderes Dateisystem – nach <i>resume</i> waren alle 12 Dateien (480 MB) inhaltsgleich im Archiv, ohne Reste."),
    ("h1", "11  Code-Review (Sicherheit, Stabilität, Ausfallsicherheit)"),
    ("table", ["#", "Fund", "Behebung"], REVIEW_DE, [0.06, 0.52, 0.42]),
    ("h2", "Bekannte Grenzen"),
    ("ul", [
        "Oberfläche nur mit Tk-Attrappe getestet (keine Anzeige in der Build-Umgebung) – Optik bitte unter Windows/macOS prüfen.",
        "Das Repository dm5cq/BildZwilling enthielt keinen Code; der Stil wurde nach den bekannten Vorgaben (Dunkelgrau/Orange, graue Titelleiste, Info-Dialog grau/weiß mit Icon) nachgebaut.",
        "Kopie über Laufwerksgrenzen: Erstellungsdatum (Windows), NTFS-Alternate-Data-Streams und macOS-Finder-Tags werden nicht übernommen – Archiv möglichst auf dasselbe Laufwerk legen.",
        "Netzlaufwerke haben keinen Papierkorb – die App erkennt das und erlaubt dort nur bewusstes endgültiges Löschen.",
    ]),
    ("h1", "12  Original-Prompt"),
    ("p", "Idee und Konzept: Stefan J. Kaiser DM5CQ / OE8KKS. Der Prompt wurde in zwei Nachrichten gesendet und ist unverändert wiedergegeben (auch als <i>PROMPT.md</i> / <i>PROMPT.txt</i>)."),
    ("h2", "Nachricht 1"),
    ("quote", MSG1),
    ("h2", "Nachricht 2"),
    ("quote", MSG2),
    ("h2", "Nachtrag zu Version 1.0.1"),
    ("quote", MSG3),
    ("h2", "Abgeleitete Anforderungen"),
    ("table", ["Nr.", "Anforderung", "Umsetzung"], [
        ["A1", "Stil wie BildZwilling", "Dunkelgrau/Orange/Weiß, graue Titelleiste, Info-Dialog, DE/EN, Barrierefreiheit"],
        ["A2", "Zuverlässige Analyse", "Größe → Schnell-Prüfsumme → BLAKE2b-256 → Byte-Vergleich"],
        ["A3/A4", "Ins Archiv verschieben, nichts löschen", "Verifiziertes Verschieben; Löschen nur nach Freigabe"],
        ["A5", "Pfade exakt abbilden", "Laufwerk/UNC/Volume als Ordnerebene im Archiv"],
        ["A6", "Alle gängigen Formate", "Inhaltsvergleich für jede Datei + Kategorien"],
        ["A7", "Portable EXE + macOS", "build-exe.bat, build-macos.sh"],
        ["A8", "Code-Review", "Kapitel 11, docs/CODE-REVIEW.md"],
        ["A9", "Nach Crash weitermachen", "Journal + Cache + Wiederherstellung"],
        ["A10–A13", "QuickDoku DE/EN, Technik mit Prompt, Prompt separat, ZIP", "dieses Paket"],
    ], [0.1, 0.38, 0.52]),
]

en = [
    ("h1", "1  Overview"),
    ("p", "DateiZwilling is a clean-up tool for forgotten files with identical content. It compares the <b>content</b> (not the name) of any files in several source folders and moves duplicates into an archive that mirrors the original paths exactly. Final removal only happens after explicit release. The app is written in Python 3, uses only the standard library for logic and storage (sqlite3, hashlib, tkinter) and is shipped with PyInstaller as a portable Windows EXE or macOS app. Pillow is optional (image preview)."),
    ("table", ["Goal", "Implementation"], [
        ["Reliability", "Multi-stage content comparison, byte-by-byte check before every move"],
        ["No data loss", "Move instead of delete, verification, never overwrite, release before removal"],
        ["Fault tolerance", "Write-ahead journal, checksum cache, automatic repair and resume"],
        ["Traceability", "Exact path mirroring, CSV manifest per run in the archive, log files, HTML report"],
        ["Portability", "Onefile EXE, data next to the EXE; macOS build script"],
    ], [0.25, 0.75]),
    ("h1", "2  Architecture"),
    ("table", ["Module", "Purpose"], MODULES_EN, [0.32, 0.68]),
    ("p", "The interface runs in the main thread. Scan, archiving, undo and clean-up run in a background thread and report progress, log lines and results through a queue that the interface polls every 100 ms. Pause and cancel are implemented through a thread-safe <i>Control</i> object at checkpoints (every 8 MiB or between files)."),
    ("h1", "3  Detection method"),
    ("ol", [
        "<b>Directory walk</b> (os.scandir, iterative): no symlinks/junctions, no archive, system, recycle-bin and package folders, optionally no hidden files, cloud placeholders (Windows attributes OFFLINE/RECALL_ON_*, macOS SF_DATALESS), program catalogs, exclude patterns and categories. Nested source folders are merged.",
        "<b>Size groups</b>: only files of equal size continue. For candidates size/time are re-read with os.stat; hardlinks (same device + inode) count as one file.",
        "<b>Quick checksum</b>: BLAKE2b-160 over size + first and last 64 KiB. Files up to 128 KiB get the full checksum directly.",
        "<b>Full checksum</b>: BLAKE2b-256 in 1 MiB blocks, parallel (1–16 threads). If a file changes while being read (size/time before and after), it is discarded.",
        "<b>Groups</b> by (size, checksum). <b>Original</b>: files in protected folders are always kept; otherwise source folder priority, then rule (oldest/newest/shortest/longest path), then path name.",
        "<b>Before moving</b>: another byte-by-byte comparison with the kept original (can be switched off → checksum again).",
    ]),
    ("h1", "4  Archiving and path mirroring"),
    ("code", "Windows  D:\\Folder\\File.ext             → <Archive>\\D\\Folder\\File.ext\n"
             "UNC      \\\\Server\\Share\\Folder\\X       → <Archive>\\UNC\\Server\\Share\\Folder\\X\n"
             "macOS    /Volumes/HDD/Folder/X           → <Archive>/Volumes/HDD/Folder/X\n"
             "taken    …\\File.ext                      → …\\File (DZ2).ext   (never overwrite)"),
    ("p", "The whole plan of a run (including sidecars) is written to the journal in <b>one</b> transaction. Same drive: atomic <i>rename</i> + fsync of the folder. Other drive: copy to <i>target.dzpart</i> while hashing, fsync, read back and compare, copy timestamps, rename to the target name, only then remove the source. If the source cannot be removed (locked), the copy is removed again. Each run writes <i>_DateiZwilling/Archivierung-Lauf-NNNNN.csv</i> into the archive (time, status, original path, archive path, original, size, checksum)."),
    ("h2", "Sidecar files"),
    ("p", "<i>name.ext.xmp/.pp3/.dop/.on1</i>, <i>name.xmp/.aae/.thm</i> and Capture One <i>CaptureOne/Settings*/name.ext.cos</i> move with the duplicate – but only if the duplicate itself was moved successfully and a stem-matched XMP does not also belong to a file that stays (RAW+JPEG)."),
    ("h1", "5  Fault tolerance"),
    ("code", STATE_EN),
    ("ul", [
        "Every state change is committed to SQLite (WAL, synchronous=FULL) <b>before</b> the action.",
        "On start <i>recover_all()</i> repairs all open runs: a completed rename is detected (target present, checksum matches), half copies are deleted, verified copies completed. The app then offers to continue the run where it stopped.",
        "If the archive drive is not reachable, nothing is changed; the run stays open.",
        "Scan: checksums are written to the cache continuously (≤ 2 s / 300 files), keyed by path + size + modification time. An interrupted scan resumes without re-reading files already checked.",
        "Closing during a run: a scan is cancelled cleanly (cache saved); archiving is paused and resumed on the next start.",
        "Corrupt database: self-check (quick_check), backup as <i>.defekt-date</i>, re-creation. The CSV manifest in the archive remains as independent evidence.",
        "Crash log via faulthandler, unhandled exceptions (also in threads) are logged.",
    ]),
    ("h1", "6  Data storage"),
    ("table", ["Location / table", "Content"], [
        ["DateiZwilling-Daten\\ (next to the EXE)", "Portable data folder; without write access: %LOCALAPPDATA%\\DateiZwilling or ~/Library/Application Support/DateiZwilling"],
        ["dateizwilling.db: hash_cache", "Path, size, modification time, quick/full checksum (entries unused > 1 year are removed)"],
        ["sessions / dupes", "Scan sessions (sources, archive, options, phase, statistics) and duplicate groups incl. selection"],
        ["runs / journal", "Archive and undo runs and every single step with its state"],
        ["einstellungen.json", "Interface and checking settings (written atomically)"],
        ["Protokolle\\", "dateizwilling.log (5 × 5 MB rotating), absturz.log"],
    ], [0.35, 0.65]),
    ("h1", "7  File formats and protection rules"),
    ("p", "Because content is compared, every format is supported. Categories: Office (Word, Excel, PowerPoint, Access, Publisher, Visio, OneNote, Project, Outlook files, LibreOffice, iWork, WPS), PDF/e-books, images (incl. FITS/XISF for Seestar), camera RAW (Fujifilm, Nikon, Canon, Panasonic, OM System, Leica, Hasselblad, Sony, Pentax, Sigma, DJI, Insta360, GoPro …), Adobe, Affinity (incl. .af), Capture One, video, audio, archives, text/code, other."),
    ("table", ["Rule", "Examples"], [
        ["Never scanned (system files)", "~$*, .~lock.*#, Thumbs.db, desktop.ini, .DS_Store, ._*, *.lnk, *.dzpart, pagefile.sys"],
        ["Never entered (folders)", "$Recycle.Bin, System Volume Information, Windows, Program Files, .Trashes, .git, node_modules, @eaDir, #recycle, _DateiZwilling"],
        ["Protected packages", ".app, .photoslibrary, .lrdata, .lrlibrary, .cocatalog, .fcpbundle, .logicx, .imovielibrary, .affinitycatalog …"],
        ["Protected catalogs (option)", ".lrcat, .cocatalogdb, .cosessiondb, .pst, .ost, SQLite WAL/SHM"],
        ["Further", "Symlinks/junctions, hardlinks, cloud placeholders, open Office documents, protected folders"],
    ], [0.3, 0.7]),
    ("h1", "8  Command line"),
    ("code", "DateiZwilling.exe --cli scan -s D:\\Data -s E:\\Backup -a F:\\DZ-Archive\n"
             "        [-p protected] [-x *.tmp] [--category office --category pdf]\n"
             "        [--keep oldest|newest|shortest|longest] [--workers 2] [--no-verify]\n"
             "        [--report report.html] [--csv report.csv] [--archive-now --yes]\n"
             "DateiZwilling.exe --cli resume | runs | undo [--run N] | purge --run N [--permanent] --yes"),
    ("h1", "9  Build and distribution"),
    ("ul", [
        "<b>Windows:</b> <i>build-exe.bat</i> – checks Python ≥ 3.10 and tkinter, creates .venv, installs Pillow + PyInstaller, runs all tests and produces <i>dist\\DateiZwilling.exe</i> (onefile, windowed, icon, version info).",
        "<b>macOS:</b> <i>build-macos.sh</i> – .app with bundle ID, ad-hoc signature and DMG.",
        "Code signing (optional) avoids SmartScreen/Gatekeeper warnings.",
    ]),
    ("h1", "10  Tests"),
    ("p", f"{N_TESTS} automated tests (<i>python -m unittest discover -s tests</i>) cover scanning, archiving, path mirroring, cross-drive moves, undo, clean-up, protection rules, database corruption, six crash scenarios and a complete interface flow (with a Tk stub). In addition: real test with <i>kill -9</i> during a copy to another file system – after <i>resume</i> all 12 files (480 MB) were in the archive with identical content and no leftovers."),
    ("h1", "11  Code review (security, stability, fault tolerance)"),
    ("table", ["#", "Finding", "Fix"], REVIEW_EN, [0.06, 0.52, 0.42]),
    ("h2", "Known limitations"),
    ("ul", [
        "Interface tested only with a Tk stub (no display in the build environment) – please check the look on Windows/macOS.",
        "The repository dm5cq/BildZwilling contained no code; the style was rebuilt from the known requirements (dark grey/orange, grey title bar, grey/white About dialog with icon).",
        "Cross-drive copy: creation date (Windows), NTFS alternate data streams and macOS Finder tags are not preserved – put the archive on the same drive where possible.",
        "Network drives have no recycle bin – the app detects this and only allows deliberate permanent deletion there.",
    ]),
    ("h1", "12  Original prompt"),
    ("p", "Idea and concept: Stefan J. Kaiser DM5CQ / OE8KKS. The prompt was sent in German in two messages and is reproduced unchanged (also available as <i>PROMPT.md</i> / <i>PROMPT.txt</i>)."),
    ("h2", "Message 1"),
    ("quote", MSG1),
    ("h2", "Message 2"),
    ("quote", MSG2),
    ("h2", "Addendum for version 1.0.1"),
    ("quote", MSG3),
    ("h2", "Derived requirements"),
    ("table", ["No.", "Requirement", "Implementation"], [
        ["A1", "Same style as BildZwilling", "Dark grey/orange/white, grey title bar, About dialog, DE/EN, accessibility"],
        ["A2", "Reliable analysis", "Size → quick checksum → BLAKE2b-256 → byte comparison"],
        ["A3/A4", "Move to archive, delete nothing", "Verified move; deletion only after release"],
        ["A5", "Mirror paths exactly", "Drive/UNC/volume as folder level in the archive"],
        ["A6", "All common formats", "Content comparison for every file + categories"],
        ["A7", "Portable EXE + macOS", "build-exe.bat, build-macos.sh"],
        ["A8", "Code review", "Chapter 11, docs/CODE-REVIEW.md"],
        ["A9", "Continue after crash", "Journal + cache + recovery"],
        ["A10–A13", "Quick guide DE/EN, technical doc with prompt, prompt separately, ZIP", "this package"],
    ], [0.1, 0.38, 0.52]),
]

build(os.path.join(PDF, "Technische_Beschreibung_DE.pdf"), "DateiZwilling – Technische Beschreibung",
      "Version 1.0.1 · Architektur, Verfahren, Ausfallsicherheit, Code-Review, Prompt", de, FOOT_DE, ICON, "de")
build(os.path.join(PDF, "Technical_Description_EN.pdf"), "DateiZwilling – Technical Description",
      "Version 1.0.1 · Architecture, methods, fault tolerance, code review, prompt", en, FOOT_EN, ICON, "en")
print("tech ok")
