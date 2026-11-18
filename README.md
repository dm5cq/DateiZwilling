# DateiZwilling 1.0.1

**Inhaltsgleiche Dateien finden & sicher archivieren** – im Stil von BildZwilling.

DateiZwilling durchsucht beliebig viele Ordner (lokal, USB, NAS, pCloud, OneDrive, Nextcloud …) nach Dateien mit **identischem Inhalt** – egal wie sie heißen – und verschiebt die Duplikate in einen Archivordner, der die **Originalpfade exakt abbildet**. Gelöscht wird erst, wenn du das Archiv ausdrücklich freigibst.

* Alle Dateiformate (Inhaltsvergleich): Word, Excel, PowerPoint, Access, Publisher, Visio, OneNote, LibreOffice, iWork, PDF, alle Bild- und RAW-Formate, Adobe (PSD, AI, INDD, Premiere, After Effects …), Affinity, Capture One, Video, Audio, Archive …
* Zuverlässig: Größe → Schnell-Prüfsumme → BLAKE2b-256 → Byte-für-Byte-Vergleich vor dem Verschieben
* Ausfallsicher: Journal + Prüfsummen-Cache – nach Absturz geht es an der Abbruchstelle weiter
* Rückgängig, HTML/CSV-Bericht, geschützte Ordner, Begleitdateien (XMP/COS), Kommandozeilenmodus
* Deutsch/Englisch, hoher Kontrast, Schriftgröße, Sprachausgabe
* Portable Windows-EXE, macOS-App

## Bauen

| System | Befehl | Ergebnis |
|---|---|---|
| Windows | Doppelklick auf `build-exe.bat` | `dist\DateiZwilling.exe` (portabel) |
| macOS | `./build-macos.sh` | `dist/DateiZwilling.app` + `.dmg` |
| direkt starten | `python DateiZwilling.py` | – |

Voraussetzung: Python 3.10+ (python.org, inkl. Tcl/Tk). Die Build-Skripte legen eine virtuelle Umgebung an, installieren Pillow + PyInstaller und führen vorher die Tests aus.

## Kommandozeile

```
DateiZwilling.exe --cli scan -s D:\Daten -s E:\Sicherung -a F:\DZ-Archiv --report bericht.html
DateiZwilling.exe --cli scan -s D:\Daten -a F:\DZ-Archiv --archive-now --yes
DateiZwilling.exe --cli resume        (unterbrochene Läufe/Scans fortsetzen)
DateiZwilling.exe --cli runs          (Läufe anzeigen)
DateiZwilling.exe --cli undo --run 3  (Archivierung rückgängig)
DateiZwilling.exe --cli purge --run 3 (nach Freigabe in den Papierkorb)
```

## Ordner

```
DateiZwilling.py           Startpunkt
dateizwilling/             Programmcode (scanner, archiver, state, gui, cli …)
assets/                    Icons
tests/                     automatische Tests (python -m unittest discover -s tests)
Dokumentation/             PDF: QuickGuide DE/EN, Technische Beschreibung DE/EN
docs/                      Code-Review, Prompt, Bilder
build-exe.bat              Windows-Build
build-macos.sh             macOS-Build
```

## Copyright

© 2026 Stefan J. Kaiser DM5CQ / OE8KKS · Idee und Konzept · Umsetzung: Claude (Anthropic), 18.11.2026
Lizenz: GNU GPL v3 (siehe `LICENSE`).
