# Änderungen

## 2.0.0 – 18.11.2026 (Korrektur Testpaket)
* Test `test_cloud_and_risky_detection` schlug unter Windows fehl, weil Testordner in `%LOCALAPPDATA%\Temp` liegen (korrekt als Programmdaten erkannt). Test prüft jetzt einen normalen Datenordner. App-Code unverändert.

## 2.0.0 – 18.11.2026
**Info & Rechtliches**
* Neuer, kompakter Info-Dialog (automatische Größe): Idee & Konzept Stefan J. Kaiser DM5CQ / OE8KKS, Umsetzung Claude (Anthropic), Lizenz GNU GPL v3; Knöpfe Lizenz, Haftungsausschluss, Protokolle.
* Haftungsausschluss (auch einmalig beim ersten Start je Hauptversion), GPL-Text in der App.

**Sicherheit**
* Bereinigen vergleicht die Archivkopie vorher Byte für Byte mit dem Original (S1).
* Speicherplatz-Prüfung; bei vollem Laufwerk wird der Lauf angehalten und kann fortgesetzt werden (S2).
* FAT32-Grenze (4 GB) und ungültige Dateinamen auf FAT/exFAT/NTFS (S3).
* Datenbanksicherung im Archiv + „Archiv importieren“ (S4); einzelne Dateien wiederherstellen (S5).
* Warnungen: Archiv im Cloud-Sync-Ordner (S6), Laufwerk/System-/Benutzerordner als Quelle (S7).
* Erstellungsdatum/Attribute bei Kopien (S8), Build mit Lock-Datei, SHA-256 und optionaler Signatur (S9), anonymisierte Berichte/Diagnose (S10).

**Stabilität**
* Kein Standby während Läufen (ST1), Warten auf getrennte Laufwerke (ST2), Vorschau im Hintergrund (ST3), Dateiliste auf Festplatte + Seitenansicht (ST4), SSD/HDD-Erkennung (ST5), Datenbankpflege (ST6), Testplan + Diagnose-Export (ST7).

**Funktionen**
* Vorschau für PDF, Office/OpenDocument/iWork, RAW, Video, STL/OBJ (3D-Ansicht), 3MF, G-Code (F1).
* Doppelte Ordner (F2), Ordnerregeln „bevorzugt“/„nie Original“ (F3), Archiv-Browser (F4), Drag & Drop (F5), Statistik (F6), Zeitplan für Berichte (F7), nahezu gleiche Dokumente (F8).
* Neue Kategorie „3D-Druck & CAD“ (STL, 3MF, OBJ, STEP, G-Code, Harzdruck-Formate, CAD …).

## 1.0.1 – 18.11.2026
* Alle Meldungen und Rückfragen als eigene dunkle Dialoge (Dunkelgrau, weiße Schrift, orangener Standardknopf) statt weißer Windows-Fenster.
* Titelleiste auch bei Info-, Einstellungs- und Bereinigungsdialog zuverlässig dunkelgrau (Neuzeichnen nach dem Anzeigen).
* Fenstergröße passt sich dem Bildschirm an; gespeicherte Größe wird nur übernommen, wenn sie passt; kleine Bildschirme starten maximiert.
* Scan/Pause/Abbrechen und die Archivier-Knöpfe sind fest unten verankert und immer sichtbar; Seitenleiste und Einstellungen scrollen bei Bedarf.
* Checkboxen und Optionsfelder dunkelgrau, ausgewählt orange mit weißem Haken.
* PDF-Dokumentation liegt im ZIP im Ordner „Dokumentation“.

## 1.0.0 – 18.11.2026
* Erste Version: Dublettensuche für alle Dateiformate, Archiv mit exakter Pfadabbildung,
  Absturz-Wiederherstellung, Rückgängig, Bereinigen nach Freigabe, Begleitdateien,
  geschützte Ordner/Kataloge, Cloud-Platzhalter, HTML/CSV-Bericht, Kommandozeile,
  DE/EN, hoher Kontrast, Schriftgröße, Sprachausgabe, portable EXE, macOS-Build.
