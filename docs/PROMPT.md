# DateiZwilling – Original-Prompt

**Idee und Konzept:** Stefan J. Kaiser DM5CQ / OE8KKS
**Umsetzung:** Claude (Anthropic), 18.11.2026
**Version:** 2.0.0

Der Prompt wurde in zwei Nachrichten gesendet und ist hier unverändert (inkl. Schreibweise) wiedergegeben.

---

## Nachricht 1

> Ich benötige eine App im gleichen Stiel wie BildZwilling die App soll DateiZwilling heissen! Sie soll genau so zuferlässig verzeichnisse nach Dateidubletten analysieren und diese in ein definiertes Archiv Verzeichnis verschieben. Es wird zueerst nichts gelöscht. Die Dateipfade müssen im Archiv genau so wieder abgebildet sein. Es müssen alle gängigen Dateiformate untersützt werden. Angefangen von den Office Anwendugen Word Excel powerpoint Access, pub

## Nachricht 2

> publisher, alles Office Derivate, Zusätzlich natürlich auch alle Bilddateien wie im BildZwilling und zusätzlich noch PDF oder die ADOBE Suite oder die Files von Affinity Suite oder Capture One Kurz um ein Bereinigungs tool für vergessene gleiche Dateiinhalte. Nutzbar auch als portable.Exe oder dann auch zum compailieren für MacOS. Mach dnn auch immer ein Code Review auf Sicherheit, stabilität und ausfallsicherheit. Wenn die App crashen sollte muss es an der aufgehörten position wieder weiter gehen usw. Erstelle eine QuickDoku als PDF in Deutsch und in English. Die Doku zur Tschnischen Beschreibung soll auch den Promt enthalten,. Zusätzlich noch den Promt separat exportieren. Alles als Zip Das Layout wie die BildZwilling App - Leg los!

---

## Aus dem Prompt abgeleitete Anforderungen

| Nr. | Anforderung | Umsetzung |
|----|----|----|
| A1 | Gleicher Stil wie BildZwilling | Dunkelgrau/Orange/Weiß, graue Titelleiste (Windows), Info-Dialog grau mit weißer Schrift und App-Icon, DE/EN, Barrierefreiheit |
| A2 | Zuverlässige Dublettenanalyse | Inhaltsvergleich: Größe → Schnell-Prüfsumme → BLAKE2b-256 → Byte-für-Byte-Vergleich vor dem Verschieben |
| A3 | Duplikate in definiertes Archiv verschieben | Archivordner frei wählbar, Verschieben mit Verifikation |
| A4 | Zuerst nichts löschen | Löschen nur über „Archiv bereinigen“ nach ausdrücklicher Freigabe (Eingabe LÖSCHEN), bevorzugt Papierkorb |
| A5 | Pfade im Archiv exakt abbilden | `D:\Ordner\Datei` → `<Archiv>\D\Ordner\Datei`, UNC → `<Archiv>\UNC\Server\Freigabe\…`, macOS `/Volumes/…` → `<Archiv>/Volumes/…` |
| A6 | Alle gängigen Formate | Inhaltsvergleich funktioniert für **jede** Datei; Kategorien für Office (inkl. Access, Publisher, Visio, OneNote, LibreOffice, iWork), PDF, Bilder, RAW, Adobe, Affinity, Capture One, Video, Audio, Archive, Text |
| A7 | Portable EXE + macOS | PyInstaller-Onefile-EXE (Daten neben der EXE), `build-macos.sh` für .app/.dmg |
| A8 | Code-Review Sicherheit/Stabilität/Ausfallsicherheit | `docs/CODE-REVIEW.md`, 32 automatische Tests inkl. simulierter Abstürze |
| A9 | Nach Absturz an der Abbruchstelle weitermachen | Write-Ahead-Journal in SQLite, Prüfsummen-Cache, automatische Reparatur halbfertiger Schritte beim Start |
| A10 | QuickDoku PDF Deutsch + Englisch | `QuickGuide_DE.pdf`, `QuickGuide_EN.pdf` |
| A11 | Technische Beschreibung mit Prompt | `Technische_Beschreibung_DE.pdf`, `Technical_Description_EN.pdf` |
| A12 | Prompt separat | diese Datei (`PROMPT.md`) und `PROMPT.txt` |
| A13 | Alles als ZIP | `DateiZwilling-2.0.0.zip` |

## Nachtrag 1.0.1

> und über das INFO ist die Menüzeile in Weiss dargesteltl es soll alles in Dunkelgrau mit wiesserschrift und orangen akzenten dargestellt werden. - Die PDF Dukomente fehlen noch. die Fenster und Programmdatei passen nicht immer - es muss zuerst auf Vollbild gegangen werden damit der Starte Scan Button erscheint. dass sollte alles sichtbar sien - oder dynamisch skaliert. ggf. damit es gut aussiehe. Die Weissen Checkboxen sollten grau mit weiss oder orange sein


## Nachtrag 2.0 – Rückmeldung zum Info-Dialog

> kürze den Text hier - das ist unübersichtlich mach es professioneller zudem ist unter der Text gequetscht. Idee & Konzept Stefan J. Kaiser Hinweis auf GNU3 lizenz usw was da hinen muss auch ein Haftungsausschluß beim verwneden der App! Welche Verbesserungen und im Codereview sihst du auch in punkto sicherheit udn stabilität etc. befor du es umsetzt bitte zuerst Vorschleäge ich gebe dann den nächsten Entwicklungsschritt 2.0 frei

## Freigabe 2.0

> Empfehlung plus alles andere umsetzten! auch mit einbauen 3D Druck dateien wie STL etc.

### Umfang 2.0 (freigegeben: alle Vorschläge)

| Bereich | Punkte |
|---|---|
| A – Info-Dialog | kompakt, automatische Größe, Idee & Konzept, Umsetzung, GPL v3, Lizenz-Anzeige, Haftungsausschluss (auch beim ersten Start), Protokolle |
| B – Sicherheit | S1 Byte-Vergleich vor dem Löschen · S2 Speicherplatz-Prüfung · S3 FAT32/Dateinamen · S4 DB-Sicherung + Archiv-Import · S5 einzelne Dateien wiederherstellen · S6 Cloud-Sync-Warnung · S7 Warnung Laufwerk/Systemordner · S8 Erstellungsdatum/Attribute · S9 Build-Härtung (Lock-Datei, SHA-256, Signatur optional) · S10 Anonymisierung |
| C – Stabilität | ST1 Standby verhindern · ST2 Warten bei getrenntem Laufwerk · ST3 Vorschau im Hintergrund · ST4 Dateiliste auf Festplatte, Seiten statt 5000-Grenze · ST5 SSD/HDD automatisch · ST6 Datenbankpflege · ST7 Testplan + Diagnose-Export |
| D – Funktionen | F1 Vorschauen (PDF, Office, RAW, Video, STL/OBJ, 3MF, G-Code) · F2 doppelte Ordner · F3 Ordnerregeln · F4 Archiv-Browser · F5 Drag & Drop · F6 Statistik · F7 Zeitplan · F8 nahezu gleiche Dokumente |
| Zusatz | Kategorie „3D-Druck & CAD“: STL, 3MF, OBJ, AMF, PLY, STEP/IGES, G-Code/BGCode, Harz-Formate (CTB, Photon, Lychee …), Slicer-Projekte, FreeCAD, Fusion 360, OpenSCAD, Blender, SketchUp, SolidWorks, Inventor, DWG/DXF |
