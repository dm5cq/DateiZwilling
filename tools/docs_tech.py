import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from pdfkit_dz import build  # noqa: E402

ROOT = sys.argv[1]
ICON = os.path.join(ROOT, "assets", "icon.png")
OUT = os.path.join(ROOT, "docs")
PDF = os.path.join(ROOT, "Dokumentation")
os.makedirs(PDF, exist_ok=True)
FOOT_DE = "© 2026 Stefan J. Kaiser DM5CQ / OE8KKS · Idee & Konzept · Umsetzung: Claude (Anthropic) · GNU GPL v3"
FOOT_EN = "© 2026 Stefan J. Kaiser DM5CQ / OE8KKS · Idea & concept · Implementation: Claude (Anthropic) · GNU GPL v3"

prompt = open(os.path.join(OUT, "PROMPT.md"), encoding="utf-8").read()
MSG1 = prompt.split("## Nachricht 1")[1].split("## Nachricht 2")[0].strip().lstrip("> ").strip()
MSG2 = prompt.split("## Nachricht 2")[1].split("---")[0].strip().lstrip("> ").strip()
N_TESTS = sys.argv[2]
MSG3 = prompt.split("## Nachtrag 1.0.1")[1].split("## Nachtrag 2.0")[0].strip().lstrip("> ").strip()
MSG4 = prompt.split("## Nachtrag 2.0 – Rückmeldung zum Info-Dialog")[1].split("## Freigabe 2.0")[0].strip().lstrip("> ").strip()
MSG5 = prompt.split("## Freigabe 2.0")[1].split("###")[0].strip().lstrip("> ").strip()

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
    ["dateizwilling/report.py", "HTML- und CSV-Bericht, Statistik je Kategorie, Anonymisierung"],
    ["dateizwilling/preview.py", "Vorschauen: Bilder, RAW-JPEG, PDF, Office/3MF-Miniaturen, G-Code, STL/OBJ-3D-Ansicht, Video, Explorer/Quick Look"],
    ["dateizwilling/content.py", "Text-Fingerabdruck für nahezu gleiche Dokumente (OOXML, OpenDocument, PDF, Text)"],
    ["dateizwilling/scheduler.py", "Zeitplan über Windows-Aufgabenplanung / macOS launchd"],
    ["dateizwilling/gui_extra.py", "Dialoge: Info, Lizenz, Haftungsausschluss, Diagnose, Statistik, Archiv-Browser, Zeitplan"],
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
    ["dateizwilling/report.py", "HTML and CSV report, statistics per category, anonymization"],
    ["dateizwilling/preview.py", "Previews: images, RAW JPEG, PDF, Office/3MF thumbnails, G-code, STL/OBJ 3D view, video, Explorer/Quick Look"],
    ["dateizwilling/content.py", "Text fingerprint for near-identical documents (OOXML, OpenDocument, PDF, text)"],
    ["dateizwilling/scheduler.py", "Schedule via Windows Task Scheduler / macOS launchd"],
    ["dateizwilling/gui_extra.py", "Dialogs: about, license, disclaimer, diagnostics, statistics, archive browser, schedule"],
    ["dateizwilling/i18n.py / config.py", "Texts DE/EN, settings (saved atomically)"],
]

REVIEW_DE = [
    ["S1", "Bereinigen: Archivkopie wird vorher Byte für Byte mit dem Original verglichen", "umgesetzt, Test"],
    ["S2", "Speicherplatz vorab und je Datei; bei Mangel Lauf angehalten (bleibt offen)", "umgesetzt, Test"],
    ["S3", "FAT32-Grenze 4 GB; ungültige Namen auf FAT/exFAT/NTFS ersetzt", "umgesetzt, Test"],
    ["S4", "Datenbanksicherung im Archiv; Archiv-Import aus CSV-Protokollen", "umgesetzt, Test"],
    ["S5", "Einzelne Dateien wiederherstellen (Begleitdateien folgen)", "umgesetzt, Test"],
    ["S6/S7", "Warnung Cloud-Sync-Archiv; Laufwerk/System-/Benutzerordner als Quelle", "umgesetzt, Test"],
    ["S8", "Erstellungsdatum und Attribute bei Kopien (Windows)", "umgesetzt"],
    ["S9", "Lock-Datei, SHA-256, optionale Signatur", "Build-Skripte"],
    ["S10", "Anonymisierte Berichte und Diagnose", "umgesetzt, Test"],
    ["ST1–ST7", "Kein Standby, Warten auf Laufwerke, Vorschau-Thread, Dateiliste auf Platte + Seiten, SSD/HDD, DB-Pflege, Testplan + Diagnose", "umgesetzt, Tests"],
    ["R14", "Ordner-Archivierung erfasste auch Kopien außerhalb der Ordner", "behoben, Test"],
    ["R15", "Ein Thread je Vorschau", "ein Worker, neueste Anfrage gewinnt"],
    ["R16", "% in Pfaden der Zeitplan-Datei", "%% maskiert"],
    ["R17", "Diagnose mit vollständigen Pfaden", "anonymisiert"],
    ["R18", "Alte Ergebnisliste unverträglich", "Schema-Migration"],
    ["R19", "Titel überdeckte Kopfleisten-Knöpfe", "Packreihenfolge"],
    ["R20", "Dateihandle-Leck /sys/block", "with open"],
]
REVIEW_EN = [
    ["S1", "Clean-up: archived copy compared byte by byte with the original first", "implemented, test"],
    ["S2", "Free space checked up front and per file; run paused if short (stays open)", "implemented, test"],
    ["S3", "FAT32 4 GB limit; invalid names on FAT/exFAT/NTFS replaced", "implemented, test"],
    ["S4", "Database backup in the archive; archive import from CSV manifests", "implemented, test"],
    ["S5", "Restore single files (sidecars follow)", "implemented, test"],
    ["S6/S7", "Warning for cloud-sync archive; drive/system/user folder as source", "implemented, test"],
    ["S8", "Creation date and attributes on copies (Windows)", "implemented"],
    ["S9", "Lock file, SHA-256, optional signing", "build scripts"],
    ["S10", "Anonymized reports and diagnostics", "implemented, test"],
    ["ST1–ST7", "No standby, wait for drives, preview thread, file list on disk + pages, SSD/HDD, DB maintenance, test plan + diagnostics", "implemented, tests"],
    ["R14", "Folder archiving also caught copies outside the folders", "fixed, test"],
    ["R15", "One thread per preview", "one worker, latest request wins"],
    ["R16", "% in paths of the schedule file", "escaped as %%"],
    ["R17", "Diagnostics with full paths", "anonymized"],
    ["R18", "Old result list incompatible", "schema migration"],
    ["R19", "Title covered header buttons", "packing order"],
    ["R20", "File handle leak /sys/block", "with open"],
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
    ("h1", "8  Neu in Version 2.0"),
    ("table", ["Funktion", "Technik"], [
        ["Doppelte Ordner (F2)", "Je Ordner (rekursiv) wird eine reihenfolgeunabhängige Signatur aus relativem Pfad + Prüfsumme aller Dateien gebildet. Ein Ordner gilt als doppelt, wenn alle geprüften Dateien in Duplikatgruppen liegen und Signatur + Anzahl übereinstimmen. Nur oberste Ordner werden gemeldet; beim Archivieren werden nur die Dateien dieser Ordner verschoben."],
        ["Nahezu gleiche Dokumente (F8)", "Text aus OOXML (word/ppt/xl), OpenDocument, PDF (pypdfium2) und Textdateien, Leerraum normalisiert, BLAKE2b-192 ('t:'-Prüfsumme, im Cache). Eigene Ansicht und Rückfrage; Text-Vergleich unmittelbar vor dem Verschieben und Bereinigen."],
        ["Vorschau (F1, ST3)", "Ein Hintergrund-Thread; Quellen nacheinander: Pillow, eingebettetes JPEG (RAW), PDF-Seite, ZIP-Miniatur (Office/iWork/3MF), G-Code-Base64-Bilder, eigene 3D-Darstellung für STL/OBJ (isometrisch, flach schattiert), ffmpeg-Standbild, Windows-Explorer-Miniatur bzw. macOS Quick Look."],
        ["Ordnerregeln (F3)", "Reihenfolge der Original-Wahl: geschützt > bevorzugt > nicht 'nie Original' > Priorität der Quellordner > Regel > Pfad."],
        ["Archiv-Browser (F4, S5)", "Alle Läufe und Dateien, Suche, Teil-Wiederherstellung (plan_undo mit Eintrags-IDs), Fortsetzen offener Läufe, Archiv-Import."],
        ["Zeitplan (F7)", "Windows: .cmd-Datei + schtasks (umgeht die 261-Zeichen-Grenze); macOS: LaunchAgent-plist. Erzeugt nur HTML-Berichte."],
        ["Skalierung (ST4)", "Dateiliste in temporärer SQLite-Datei (scan-temp-N.db), Kandidaten per GROUP BY size; Anzeige in Seiten zu 1000 Gruppen."],
        ["Laufwerk weg (ST2)", "Transiente Fehler (WinError 53/64/121 …, EIO, ETIMEDOUT, ESTALE …) oder nicht erreichbare Laufwerkswurzel → Phase 'waiting', Prüfung alle 3 s, abbrechbar."],
        ["3D-Druck & CAD", "Neue Kategorie mit Modell-, Slicer-, Harzdruck- und CAD-Formaten; STL/OBJ-Vorschau ohne Zusatzbibliothek."],
    ], [0.27, 0.73]),
    ("h1", "9  Kommandozeile"),
    ("code", "DateiZwilling.exe --cli scan -s D:\\Daten -s E:\\Sicherung -a F:\\DZ-Archiv\n"
             "        [-p geschützt] [-x *.tmp] [--category office --category pdf]\n"
             "        [--keep oldest|newest|shortest|longest] [--workers 2] [--no-verify]\n"
             "        [--report bericht.html] [--csv bericht.csv] [--archive-now --yes]\n"
             "        [--prefer ordner] [--avoid ordner] [--similar] [--report-dir ordner] [--anonymize]\n"
             "DateiZwilling.exe --cli resume | runs | undo [--run N] | purge --run N [--permanent] --yes\n"
             "DateiZwilling.exe --cli import F:\\DZ-Archiv | restore --run N --file <Originalpfad>"),
    ("h1", "10  Build und Verteilung"),
    ("ul", [
        "<b>Windows:</b> <i>build-exe.bat</i> – prüft Python ≥ 3.10 und tkinter, legt .venv an, installiert Pillow, pypdfium2, tkinterdnd2 und PyInstaller, schreibt <i>build-lock.txt</i>, führt alle Tests aus und erzeugt <i>dist\\DateiZwilling.exe</i> plus SHA-256-Datei; mit <i>DZ_SIGN_CERT</i>/<i>DZ_SIGN_PASS</i> wird signiert.",
        "<b>macOS:</b> <i>build-macos.sh</i> – .app mit Bundle-ID, Ad-hoc-Signatur und DMG.",
        "Code-Signatur (optional) verhindert SmartScreen-/Gatekeeper-Hinweise.",
    ]),
    ("h1", "11  Tests"),
    ("p", f"{N_TESTS} automatische Tests (<i>python -m unittest discover -s tests</i>) decken Scan, Archivierung, Pfadabbildung, Laufwerkswechsel, Rückgängig, Bereinigen, Schutzregeln, Datenbankdefekt, sechs Absturz-Szenarien, alle Sicherheits- und Stabilitätsfunktionen von 2.0 (S1–S5, S10, ST2, ST4, ST6), doppelte Ordner, Ordnerregeln, nahezu gleiche Dokumente, 3D-Vorschauen sowie komplette Oberflächen-Abläufe (mit Tk-Attrappe) ab. Für den ersten Windows-Start liegt <i>docs/TESTPLAN.md</i> bei. Zusätzlich: Praxistest mit <i>kill -9</i> während einer Kopie auf ein anderes Dateisystem – nach <i>resume</i> waren alle 12 Dateien (480 MB) inhaltsgleich im Archiv, ohne Reste."),
    ("h1", "12  Code-Review 2.0 (Sicherheit, Stabilität, Ausfallsicherheit)"),
    ("table", ["#", "Vorschlag / Fund", "Status"], REVIEW_DE, [0.1, 0.62, 0.28]),
    ("h2", "Bekannte Grenzen"),
    ("ul", [
        "Oberfläche nur mit Tk-Attrappe getestet (keine Anzeige in der Build-Umgebung) – Optik bitte unter Windows/macOS prüfen.",
        "Explorer-Miniaturen (Rückfall-Vorschau) und Drag & Drop sind in der Build-Umgebung nicht prüfbar; bei Fehlern erscheint das Dateisymbol bzw. Ziehen ist inaktiv.",
        "Haftungsausschluss mit „soweit gesetzlich zulässig“ – keine Rechtsberatung.",
        "Kopie über Laufwerksgrenzen: Erstellungsdatum (Windows), NTFS-Alternate-Data-Streams und macOS-Finder-Tags werden nicht übernommen – Archiv möglichst auf dasselbe Laufwerk legen.",
        "Netzlaufwerke haben keinen Papierkorb – die App erkennt das und erlaubt dort nur bewusstes endgültiges Löschen.",
    ]),
    ("h1", "13  Original-Prompt"),
    ("p", "Idee und Konzept: Stefan J. Kaiser DM5CQ / OE8KKS. Der Prompt wurde in zwei Nachrichten gesendet und ist unverändert wiedergegeben (auch als <i>PROMPT.md</i> / <i>PROMPT.txt</i>)."),
    ("h2", "Nachricht 1"),
    ("quote", MSG1),
    ("h2", "Nachricht 2"),
    ("quote", MSG2),
    ("h2", "Nachtrag zu Version 1.0.1"),
    ("quote", MSG3),
    ("h2", "Nachtrag zu Version 2.0 – Info-Dialog und Vorschläge"),
    ("quote", MSG4),
    ("h2", "Freigabe 2.0"),
    ("quote", MSG5),
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
        ["2.0", "Info-Dialog, GPL, Haftungsausschluss, alle Vorschläge S1–S10, ST1–ST7, F1–F8, 3D-Druck-Dateien", "Kapitel 8 und 12"],
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
    ("h1", "8  New in version 2.0"),
    ("table", ["Feature", "Technique"], [
        ["Duplicate folders (F2)", "For every folder (recursive) an order-independent signature of relative path + checksum of all files is built. A folder is a duplicate if all checked files are in duplicate groups and signature + count match. Only top-level folders are reported; archiving moves only the files of those folders."],
        ["Near-identical documents (F8)", "Text from OOXML (word/ppt/xl), OpenDocument, PDF (pypdfium2) and text files, whitespace normalized, BLAKE2b-192 ('t:' checksum, cached). Own view and confirmation; text compared again right before moving and clean-up."],
        ["Preview (F1, ST3)", "One background thread; sources in order: Pillow, embedded JPEG (RAW), PDF page, ZIP thumbnail (Office/iWork/3MF), G-code base64 images, own 3D rendering for STL/OBJ (isometric, flat shaded), ffmpeg still, Windows Explorer thumbnail or macOS Quick Look."],
        ["Folder rules (F3)", "Order of original choice: protected > preferred > not 'never original' > source priority > rule > path."],
        ["Archive browser (F4, S5)", "All runs and files, search, partial restore (plan_undo with entry IDs), continue open runs, archive import."],
        ["Schedule (F7)", "Windows: .cmd file + schtasks (avoids the 261-character limit); macOS: LaunchAgent plist. Produces HTML reports only."],
        ["Scaling (ST4)", "File list in a temporary SQLite file (scan-temp-N.db), candidates via GROUP BY size; display in pages of 1000 groups."],
        ["Drive gone (ST2)", "Transient errors (WinError 53/64/121 …, EIO, ETIMEDOUT, ESTALE …) or unreachable drive root → phase 'waiting', check every 3 s, cancellable."],
        ["3D printing & CAD", "New category with model, slicer, resin and CAD formats; STL/OBJ preview without extra library."],
    ], [0.27, 0.73]),
    ("h1", "9  Command line"),
    ("code", "DateiZwilling.exe --cli scan -s D:\\Data -s E:\\Backup -a F:\\DZ-Archive\n"
             "        [-p protected] [-x *.tmp] [--category office --category pdf]\n"
             "        [--keep oldest|newest|shortest|longest] [--workers 2] [--no-verify]\n"
             "        [--report report.html] [--csv report.csv] [--archive-now --yes]\n"
             "        [--prefer folder] [--avoid folder] [--similar] [--report-dir folder] [--anonymize]\n"
             "DateiZwilling.exe --cli resume | runs | undo [--run N] | purge --run N [--permanent] --yes\n"
             "DateiZwilling.exe --cli import F:\\DZ-Archive | restore --run N --file <original path>"),
    ("h1", "10  Build and distribution"),
    ("ul", [
        "<b>Windows:</b> <i>build-exe.bat</i> – checks Python ≥ 3.10 and tkinter, creates .venv, installs Pillow, pypdfium2, tkinterdnd2 and PyInstaller, writes <i>build-lock.txt</i>, runs all tests and produces <i>dist\\DateiZwilling.exe</i> plus a SHA-256 file; signs with <i>DZ_SIGN_CERT</i>/<i>DZ_SIGN_PASS</i> if set.",
        "<b>macOS:</b> <i>build-macos.sh</i> – .app with bundle ID, ad-hoc signature and DMG.",
        "Code signing (optional) avoids SmartScreen/Gatekeeper warnings.",
    ]),
    ("h1", "11  Tests"),
    ("p", f"{N_TESTS} automated tests (<i>python -m unittest discover -s tests</i>) cover scanning, archiving, path mirroring, cross-drive moves, undo, clean-up, protection rules, database corruption, six crash scenarios, all 2.0 safety and stability features (S1–S5, S10, ST2, ST4, ST6), duplicate folders, folder rules, near-identical documents, 3D previews and complete interface flows (with a Tk stub). <i>docs/TESTPLAN.md</i> is included for the first Windows start. In addition: real test with <i>kill -9</i> during a copy to another file system – after <i>resume</i> all 12 files (480 MB) were in the archive with identical content and no leftovers."),
    ("h1", "12  Code review 2.0 (security, stability, fault tolerance)"),
    ("table", ["#", "Proposal / finding", "Status"], REVIEW_EN, [0.1, 0.62, 0.28]),
    ("h2", "Known limitations"),
    ("ul", [
        "Interface tested only with a Tk stub (no display in the build environment) – please check the look on Windows/macOS.",
        "Explorer thumbnails (fallback preview) and drag & drop cannot be tested in the build environment; on failure the file icon is shown or dragging is inactive.",
        "Disclaimer uses “to the extent permitted by law” – no legal advice.",
        "Cross-drive copy: creation date (Windows), NTFS alternate data streams and macOS Finder tags are not preserved – put the archive on the same drive where possible.",
        "Network drives have no recycle bin – the app detects this and only allows deliberate permanent deletion there.",
    ]),
    ("h1", "13  Original prompt"),
    ("p", "Idea and concept: Stefan J. Kaiser DM5CQ / OE8KKS. The prompt was sent in German in two messages and is reproduced unchanged (also available as <i>PROMPT.md</i> / <i>PROMPT.txt</i>)."),
    ("h2", "Message 1"),
    ("quote", MSG1),
    ("h2", "Message 2"),
    ("quote", MSG2),
    ("h2", "Addendum for version 1.0.1"),
    ("quote", MSG3),
    ("h2", "Addendum for version 2.0 – About dialog and proposals"),
    ("quote", MSG4),
    ("h2", "Release of 2.0"),
    ("quote", MSG5),
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
        ["2.0", "About dialog, GPL, disclaimer, all proposals S1–S10, ST1–ST7, F1–F8, 3D printing files", "chapters 8 and 12"],
    ], [0.1, 0.38, 0.52]),
]

build(os.path.join(PDF, "Technische_Beschreibung_DE.pdf"), "DateiZwilling – Technische Beschreibung",
      "Version 2.0.0 · Architektur, Verfahren, Ausfallsicherheit, Code-Review, Prompt", de, FOOT_DE, ICON, "de")
build(os.path.join(PDF, "Technical_Description_EN.pdf"), "DateiZwilling – Technical Description",
      "Version 2.0.0 · Architecture, methods, fault tolerance, code review, prompt", en, FOOT_EN, ICON, "en")
print("tech ok")
