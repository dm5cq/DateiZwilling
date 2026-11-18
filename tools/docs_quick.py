import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from pdfkit_dz import build  # noqa: E402

ROOT = sys.argv[1]
ICON = os.path.join(ROOT, "assets", "icon.png")
OUT = os.path.join(ROOT, "docs")
FOOT_DE = "© 2026 Stefan J. Kaiser DM5CQ / OE8KKS · Idee und Konzept · Umsetzung: Claude (Anthropic), 18.11.2026"
FOOT_EN = "© 2026 Stefan J. Kaiser DM5CQ / OE8KKS · Idea and concept · Implementation: Claude (Anthropic), 18.11.2026"

FORMATS_DE = [
    ["Office", "Word (doc, docx, docm, dot, dotx, rtf), Excel (xls, xlsx, xlsm, xlsb, xlt, csv), PowerPoint (ppt, pptx, pps, ppsx, pot, potx), Access (mdb, accdb, accde), Publisher (pub), Visio (vsd, vsdx), OneNote (one), Project (mpp), Outlook (msg, oft), LibreOffice/OpenOffice (odt, ods, odp, odg …), Apple iWork (pages, numbers, key), WPS"],
    ["PDF / E-Books", "pdf, xps, epub, mobi, djvu"],
    ["Bilder", "jpg, png, gif, bmp, tif, webp, heic, avif, jxl, svg, eps, Astro/Seestar: fit, fits, xisf, ser"],
    ["Kamera-RAW", "Fujifilm raf, Nikon nef/nrw, Canon cr2/cr3/crw, Panasonic rw2, OM System orf/ori, Leica rwl/dng, Hasselblad 3fr/fff, Sony arw, Pentax pef, Sigma x3f, DJI/Insta360 dng/insp, GoPro gpr …"],
    ["Adobe", "psd, psb, ai, indd, idml, aep, prproj, xd, fla, sesx, abr, ase, xmp, dcp …"],
    ["Affinity", "af (Affinity 3), afphoto, afdesign, afpub, aftemplate, afpalette, afbrushes, afassets"],
    ["Capture One", "cos, cop, costyle, costylepack, coplate (Kataloge/Sitzungsdatenbanken sind geschützt)"],
    ["Weitere", "Video, Audio, Archive/Installer, Text/Code – und jede andere Datei (Inhaltsvergleich)"],
]
FORMATS_EN = [
    ["Office", "Word (doc, docx, docm, dot, dotx, rtf), Excel (xls, xlsx, xlsm, xlsb, xlt, csv), PowerPoint (ppt, pptx, pps, ppsx, pot, potx), Access (mdb, accdb, accde), Publisher (pub), Visio (vsd, vsdx), OneNote (one), Project (mpp), Outlook (msg, oft), LibreOffice/OpenOffice (odt, ods, odp, odg …), Apple iWork (pages, numbers, key), WPS"],
    ["PDF / e-books", "pdf, xps, epub, mobi, djvu"],
    ["Images", "jpg, png, gif, bmp, tif, webp, heic, avif, jxl, svg, eps, astro/Seestar: fit, fits, xisf, ser"],
    ["Camera RAW", "Fujifilm raf, Nikon nef/nrw, Canon cr2/cr3/crw, Panasonic rw2, OM System orf/ori, Leica rwl/dng, Hasselblad 3fr/fff, Sony arw, Pentax pef, Sigma x3f, DJI/Insta360 dng/insp, GoPro gpr …"],
    ["Adobe", "psd, psb, ai, indd, idml, aep, prproj, xd, fla, sesx, abr, ase, xmp, dcp …"],
    ["Affinity", "af (Affinity 3), afphoto, afdesign, afpub, aftemplate, afpalette, afbrushes, afassets"],
    ["Capture One", "cos, cop, costyle, costylepack, coplate (catalogs/session databases are protected)"],
    ["More", "video, audio, archives/installers, text/code – and any other file (content comparison)"],
]

de = [
    ("h1", "Was macht DateiZwilling?"),
    ("p", "DateiZwilling findet Dateien mit <b>exakt gleichem Inhalt</b> – auch wenn sie anders heißen oder in ganz anderen Ordnern liegen – und verschiebt die überflüssigen Kopien in einen <b>Archivordner</b>. Dort wird der ursprüngliche Pfad genau nachgebildet, sodass du jederzeit siehst, woher eine Datei kam. <b>Gelöscht wird nichts</b>, bis du das Archiv ausdrücklich freigibst."),
    ("note", "<b>Kurz gesagt:</b> Scannen → prüfen → archivieren → (optional) rückgängig → erst nach deiner Freigabe bereinigen."),
    ("h1", "Die Oberfläche"),
    ("img", os.path.join(OUT, "img", "schema_de.png")),
    ("table", ["Nr.", "Bereich", "Funktion"], [
        ["1", "Quellordner", "Ordner, die durchsucht werden. Reihenfolge = Priorität: Bei Duplikaten bleibt bevorzugt die Datei im oberen Ordner. Mit ↑/↓ umsortieren."],
        ["2", "Archiv / Geschützte Ordner", "Archivordner für die Duplikate. Dateien in geschützten Ordnern werden nie verschoben."],
        ["3", "Dateitypen / Original", "Kategorien eingrenzen (Standard: alle) und Regel wählen, welche Datei als Original bleibt (älteste, neueste, kürzester/längster Pfad)."],
        ["4", "Scan / Pause / Abbrechen", "Startet die Suche (F5). Pause hält sofort an, Abbrechen beendet – bereits Geprüftes bleibt erhalten."],
        ["5", "Suche, Kategorie, Sortierung", "Ergebnisliste filtern (Strg+F) und nach Ersparnis, Größe, Anzahl oder Name sortieren."],
        ["6", "Ergebnisliste", "Je Gruppe ein Original (★ behalten, grün) und die Duplikate (⇢ archivieren). Leertaste schaltet um, Enter/Doppelklick macht die Datei zum Original."],
        ["7", "Vergleich", "Original und Duplikat nebeneinander mit Vorschau (Bilder), Pfad, Größe, Datum, Prüfsumme; Öffnen oder im Ordner zeigen."],
        ["8", "Archivieren", "Ausgewählte Gruppen oder alle sichtbaren Duplikate ins Archiv verschieben."],
        ["9", "Rückgängig / Bereinigen", "Letzte Archivierung zurückholen (Strg+Z). Bereinigen entfernt geprüfte Archivdateien erst nach Freigabe."],
        ["10", "Statuszeile / Protokoll", "Fortschritt, Geschwindigkeit, Restzeit und ausklappbares Protokoll."],
    ], [0.07, 0.25, 0.68]),
    ("h1", "In 5 Schritten aufräumen"),
    ("ol", [
        "<b>Quellordner hinzufügen</b> – z. B. <i>D:\\Dokumente</i>, <i>E:\\Sicherung</i>, ein NAS-Laufwerk oder den pCloud-/OneDrive-Ordner. Den „wichtigsten“ Ordner nach oben schieben.",
        "<b>Archivordner wählen</b> – am besten auf <b>demselben Laufwerk</b> wie die meisten Duplikate (dann wird blitzschnell umbenannt statt kopiert).",
        "<b>Scan starten (F5)</b> – DateiZwilling vergleicht Größe, Schnell-Prüfsumme und vollständige BLAKE2b-Prüfsumme. Unterschiedliche Dateien mit gleichem Namen werden <b>nicht</b> als Duplikat erkannt.",
        "<b>Ergebnis prüfen</b> – Gruppe anklicken, Vergleich ansehen, bei Bedarf mit Enter ein anderes Original festlegen oder mit der Leertaste einzelne Dateien behalten.",
        "<b>Archivieren</b> – vor jedem Verschieben vergleicht DateiZwilling das Duplikat noch einmal Byte für Byte mit dem Original. Danach liegen die Kopien im Archiv; der Bericht kann als HTML/CSV exportiert werden.",
    ]),
    ("h1", "So sieht das Archiv aus"),
    ("code", "Original:   D:\\Projekte\\2024\\Angebot (Kopie).docx\n"
             "Archiv:     F:\\DZ-Archiv\\D\\Projekte\\2024\\Angebot (Kopie).docx\n\n"
             "NAS:        \\\\NAS\\daten\\Fotos\\IMG_0815.CR3\n"
             "Archiv:     F:\\DZ-Archiv\\UNC\\NAS\\daten\\Fotos\\IMG_0815.CR3\n\n"
             "macOS:      /Volumes/Fotos/2023/DSCF1234.RAF\n"
             "Archiv:     /Volumes/Archiv/DZ/Volumes/Fotos/2023/DSCF1234.RAF\n\n"
             "Protokoll:  F:\\DZ-Archiv\\_DateiZwilling\\Archivierung-Lauf-00001.csv"),
    ("p", "Begleitdateien (XMP, Capture-One-COS, AAE …) eines Duplikats wandern automatisch mit. Ist der Zielpfad bereits belegt, wird nie überschrieben, sondern <i>Name (DZ2).ext</i> verwendet."),
    ("h1", "Sicherheit: Es geht nichts verloren"),
    ("ul", [
        "<b>Nur verschieben:</b> Duplikate werden ins Archiv verschoben, nicht gelöscht.",
        "<b>Doppelte Prüfung:</b> Ist das Original inzwischen geändert oder verschwunden, bleibt das Duplikat stehen.",
        "<b>Rückgängig:</b> „Letzte Archivierung rückgängig“ (Strg+Z) bringt alles an den Originalort zurück.",
        "<b>Bereinigen nur mit Freigabe:</b> Läufe auswählen, <b>LÖSCHEN</b> eintippen – bevorzugt in den Papierkorb. Eine Archivdatei wird nur entfernt, wenn ihr Original noch existiert.",
        "<b>Geschützt:</b> Systemordner, Programm-Bibliotheken (Lightroom, Fotos, Capture One, Final Cut …), Outlook-PST, geöffnete Office-Dokumente, Verknüpfungen und Cloud-Platzhalter (es wird nichts aus der Cloud heruntergeladen).",
    ]),
    ("h1", "Absturz oder Stromausfall?"),
    ("p", "Einfach DateiZwilling neu starten. Halbfertige Schritte werden automatisch sauber abgeschlossen oder zurückgerollt. Danach fragt die App, ob der unterbrochene Lauf <b>an der Abbruchstelle fortgesetzt</b> werden soll. Ein abgebrochener Scan liest bereits geprüfte Dateien nicht noch einmal (Prüfsummen-Cache). Ist die Archiv-Festplatte nicht angeschlossen, wartet der Lauf, bis sie wieder da ist."),
    ("h1", "Tastenkürzel"),
    ("table", ["Taste", "Funktion"], [
        ["F5", "Scan starten"], ["Leertaste", "Datei behalten / archivieren umschalten"],
        ["Enter / Doppelklick", "Als Original festlegen"], ["Strg+F", "Suche"], ["Strg+Z", "Letzte Archivierung rückgängig"],
        ["Esc", "Laufenden Vorgang abbrechen"], ["F1", "Info"],
    ], [0.3, 0.7]),
    ("h1", "Einstellungen (⚙)"),
    ("ul", [
        "Sprache Deutsch/English, hoher Kontrast, Schriftgröße 90–200 %, Sprachausgabe für Meldungen.",
        "Byte-für-Byte-Vergleich vor dem Verschieben (empfohlen, Standard).",
        "Parallele Lesevorgänge: HDD/NAS 1–2, SSD 4–8.",
        "Mindestgröße, versteckte Dateien, Cloud-Platzhalter, Programm-Kataloge, Begleitdateien, Ausschlussmuster (z. B. <i>*.tmp</i>, <i>*/Cache/*</i>).",
    ]),
    ("h1", "Unterstützte Dateien"),
    ("p", "Da der <b>Inhalt</b> verglichen wird, funktioniert DateiZwilling mit <b>jedem</b> Dateiformat. Die Kategorien dienen zum Filtern:"),
    ("table", ["Kategorie", "Beispiele"], FORMATS_DE, [0.2, 0.8]),
    ("h1", "Start & portabler Betrieb"),
    ("p", "Windows: <i>DateiZwilling.exe</i> starten – keine Installation nötig. Einstellungen, Cache und Protokolle liegen im Ordner <i>DateiZwilling-Daten</i> neben der EXE (z. B. auf einem USB-Stick). Beim ersten Start warnt SmartScreen ggf.: „Weitere Informationen → Trotzdem ausführen“. macOS: <i>DateiZwilling.app</i> per Rechtsklick → Öffnen; für externe Laufwerke ggf. „Festplattenvollzugriff“ erlauben."),
]

en = [
    ("h1", "What does DateiZwilling do?"),
    ("p", "DateiZwilling finds files with <b>exactly the same content</b> – even if they have different names or live in completely different folders – and moves the redundant copies into an <b>archive folder</b>. The original path is mirrored there exactly, so you can always see where a file came from. <b>Nothing is deleted</b> until you explicitly release the archive."),
    ("note", "<b>In short:</b> scan → review → archive → (optional) undo → clean up only after your release."),
    ("h1", "The interface"),
    ("img", os.path.join(OUT, "img", "schema_en.png")),
    ("table", ["No.", "Area", "Function"], [
        ["1", "Source folders", "Folders to search. Order = priority: for duplicates the file in the upper folder is preferred as original. Reorder with ↑/↓."],
        ["2", "Archive / protected folders", "Archive folder for duplicates. Files in protected folders are never moved."],
        ["3", "File types / original", "Limit categories (default: all) and choose which file is kept as original (oldest, newest, shortest/longest path)."],
        ["4", "Scan / pause / cancel", "Starts the search (F5). Pause stops immediately, cancel ends – work already done is kept."],
        ["5", "Search, category, sort", "Filter the result list (Ctrl+F) and sort by savings, size, count or name."],
        ["6", "Result list", "One original per group (★ keep, green) and the duplicates (⇢ archive). Space toggles, Enter/double-click makes the file the original."],
        ["7", "Comparison", "Original and duplicate side by side with preview (images), path, size, date, checksum; open or show in folder."],
        ["8", "Archive", "Move selected groups or all visible duplicates into the archive."],
        ["9", "Undo / clean up", "Restore the last archiving run (Ctrl+Z). Clean up removes reviewed archive files only after release."],
        ["10", "Status bar / log", "Progress, speed, remaining time and a collapsible log."],
    ], [0.07, 0.25, 0.68]),
    ("h1", "Clean up in 5 steps"),
    ("ol", [
        "<b>Add source folders</b> – e.g. <i>D:\\Documents</i>, <i>E:\\Backup</i>, a NAS drive or your pCloud/OneDrive folder. Move the most important folder to the top.",
        "<b>Choose the archive folder</b> – ideally on the <b>same drive</b> as most duplicates (then files are renamed instantly instead of copied).",
        "<b>Start the scan (F5)</b> – DateiZwilling compares size, quick checksum and full BLAKE2b checksum. Different files with the same name are <b>not</b> treated as duplicates.",
        "<b>Review</b> – click a group, look at the comparison, press Enter to choose a different original or Space to keep individual files.",
        "<b>Archive</b> – before every move DateiZwilling compares the duplicate with the original byte by byte once more. Afterwards the copies are in the archive; the report can be exported as HTML/CSV.",
    ]),
    ("h1", "What the archive looks like"),
    ("code", "Original:   D:\\Projects\\2024\\Offer (copy).docx\n"
             "Archive:    F:\\DZ-Archive\\D\\Projects\\2024\\Offer (copy).docx\n\n"
             "NAS:        \\\\NAS\\data\\Photos\\IMG_0815.CR3\n"
             "Archive:    F:\\DZ-Archive\\UNC\\NAS\\data\\Photos\\IMG_0815.CR3\n\n"
             "macOS:      /Volumes/Photos/2023/DSCF1234.RAF\n"
             "Archive:    /Volumes/Archive/DZ/Volumes/Photos/2023/DSCF1234.RAF\n\n"
             "Manifest:   F:\\DZ-Archive\\_DateiZwilling\\Archivierung-Lauf-00001.csv"),
    ("p", "Sidecar files (XMP, Capture One COS, AAE …) of a duplicate move along automatically. If the target path is taken, nothing is overwritten – <i>name (DZ2).ext</i> is used instead."),
    ("h1", "Safety: nothing gets lost"),
    ("ul", [
        "<b>Move only:</b> duplicates are moved to the archive, not deleted.",
        "<b>Double check:</b> if the original has changed or disappeared in the meantime, the duplicate stays where it is.",
        "<b>Undo:</b> “Undo last archiving” (Ctrl+Z) moves everything back to its original location.",
        "<b>Clean up only with release:</b> select runs, type <b>DELETE</b> – recycle bin preferred. An archived file is only removed if its original still exists.",
        "<b>Protected:</b> system folders, program libraries (Lightroom, Photos, Capture One, Final Cut …), Outlook PST, open Office documents, links and cloud placeholders (nothing is downloaded from the cloud).",
    ]),
    ("h1", "Crash or power failure?"),
    ("p", "Simply restart DateiZwilling. Half-finished steps are completed or rolled back cleanly. The app then asks whether the interrupted run should <b>continue where it stopped</b>. An interrupted scan does not read already checked files again (checksum cache). If the archive drive is not connected, the run waits until it is back."),
    ("h1", "Keyboard shortcuts"),
    ("table", ["Key", "Function"], [
        ["F5", "Start scan"], ["Space", "Toggle keep / archive"], ["Enter / double-click", "Set as original"],
        ["Ctrl+F", "Search"], ["Ctrl+Z", "Undo last archiving"], ["Esc", "Cancel running operation"], ["F1", "About"],
    ], [0.3, 0.7]),
    ("h1", "Settings (⚙)"),
    ("ul", [
        "Language Deutsch/English, high contrast, font size 90–200 %, speech output for messages.",
        "Byte-by-byte comparison before moving (recommended, default).",
        "Parallel reads: HDD/NAS 1–2, SSD 4–8.",
        "Minimum size, hidden files, cloud placeholders, program catalogs, sidecar files, exclude patterns (e.g. <i>*.tmp</i>, <i>*/Cache/*</i>).",
    ]),
    ("h1", "Supported files"),
    ("p", "Because the <b>content</b> is compared, DateiZwilling works with <b>every</b> file format. Categories are used for filtering:"),
    ("table", ["Category", "Examples"], FORMATS_EN, [0.2, 0.8]),
    ("h1", "Start & portable use"),
    ("p", "Windows: start <i>DateiZwilling.exe</i> – no installation required. Settings, cache and logs are stored in the folder <i>DateiZwilling-Daten</i> next to the EXE (e.g. on a USB stick). SmartScreen may warn on first start: “More info → Run anyway”. macOS: right-click <i>DateiZwilling.app</i> → Open; allow “Full Disk Access” for external drives if needed."),
]

build(os.path.join(OUT, "QuickGuide_DE.pdf"), "DateiZwilling – QuickGuide",
      "Version 1.0.0 · Dateidubletten finden und sicher archivieren", de, FOOT_DE, ICON, "de")
build(os.path.join(OUT, "QuickGuide_EN.pdf"), "DateiZwilling – Quick Guide",
      "Version 1.0.0 · Find duplicate files and archive them safely", en, FOOT_EN, ICON, "en")
print("quick ok")
