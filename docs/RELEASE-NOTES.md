## DateiZwilling 2.0.0

Identische Dateien finden – Duplikate sicher archivieren. Portable Windows-EXE, keine Installation nötig.

### Download
- **DateiZwilling.exe** (Windows) – starten, fertig. Einstellungen und Protokolle landen im Ordner `DateiZwilling-Daten` neben der EXE.
- **DateiZwilling.exe.sha256.txt** – Prüfsumme (`certutil -hashfile DateiZwilling.exe SHA256`)
- **DateiZwilling-macOS.dmg** (macOS, Apple Silicon) – App in den Programme-Ordner ziehen, beim ersten Start Rechtsklick → Öffnen
- **QuickGuide_DE.pdf / QuickGuide_EN.pdf** – Bedienung in Kürze
- **Technische_Beschreibung_DE.pdf / Technical_Description_EN.pdf** – Technik, Code-Review, Original-Prompt

Die EXE ist nicht signiert: Windows SmartScreen fragt beim ersten Start – „Weitere Informationen“ → „Trotzdem ausführen“.

### Neu in 2.0
- Neuer Info-Dialog, GNU GPL v3, Haftungsausschluss
- **Sicherheit:** Byte-Vergleich mit dem Original vor dem endgültigen Löschen, Speicherplatz-Prüfung, FAT32-/Dateinamen-Schutz, Datenbanksicherung im Archiv + Archiv-Import, einzelne Dateien wiederherstellen, Warnungen bei Cloud-Sync-Archiv und Systemordnern
- **Stabilität:** kein Standby während Läufen, wartet bei abgezogenem USB-/Netzlaufwerk und macht automatisch weiter, Millionen Dateien, SSD/HDD-Erkennung
- **Funktionen:** Vorschau für PDF, Office, RAW, Video, **STL/OBJ in 3D**, 3MF, G-Code · doppelte Ordner · nahezu gleiche Dokumente · Ordnerregeln · Archiv-Browser · Statistik · Zeitplan · Drag & Drop
- Neue Kategorie **3D-Druck & CAD** (STL, 3MF, OBJ, STEP, G-Code, Harzdruck-Formate, CAD …)

Idee & Konzept: Stefan J. Kaiser DM5CQ / OE8KKS · Umsetzung: Claude (Anthropic) · Lizenz: GNU GPL v3
Nutzung auf eigene Gefahr – siehe Haftungsausschluss in der README.
