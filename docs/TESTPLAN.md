# DateiZwilling 2.0 – Testplan für den ersten Windows-Start (ST7)

Dauer: ca. 20 Minuten. Bitte mit einem **Testordner** arbeiten (z. B. `D:\DZ-Test` mit ein paar kopierten Dateien), nicht gleich mit den echten Daten.

Bei Auffälligkeiten: **Einstellungen → Diagnose exportieren** und die ZIP-Datei zusammen mit einem Screenshot zurückmelden.

## 1. Start und Darstellung
- [ ] Beim ersten Start erscheint der Haftungsausschluss (dunkel, „Verstanden“).
- [ ] Hauptfenster passt auf den Bildschirm; **Scan starten** ist ohne Maximieren sichtbar.
- [ ] Titelleiste von Hauptfenster, Info, Einstellungen, Archiv, Statistik, Zeitplan und allen Rückfragen ist **dunkelgrau mit weißer Schrift**.
- [ ] Checkboxen: aus = dunkelgrau, an = orange mit weißem Haken.
- [ ] Fenster verkleinern: Seitenleiste lässt sich mit dem Mausrad scrollen, Knöpfe unten bleiben sichtbar.
- [ ] Info: kompakt, nichts abgeschnitten; Knöpfe Lizenz / Haftungsausschluss / Protokolle funktionieren.

## 2. Scan
- [ ] Ordner per **Drag & Drop** auf „Quellordner“ ziehen.
- [ ] Laufwerk `C:\` als Quelle → Warnung erscheint.
- [ ] Scan mit Office-, PDF-, Bild-, RAW-, STL-/3MF-/G-Code-Dateien und kopierten Ordnern.
- [ ] Vorschau im Vergleich: Foto, PDF (erste Seite), PowerPoint, RAW, **STL (orangene 3D-Ansicht)**, G-Code-Bild.
- [ ] Ansicht „Doppelte Ordner“ zeigt kopierte Ordner als Block.
- [ ] Einstellungen → „Nahezu gleiche Dokumente“ an → eine Word-Datei öffnen und ohne Änderung neu speichern → erscheint in der Ansicht „Nahezu gleiche Dokumente“.

## 3. Archivieren und Sicherheit
- [ ] Archivieren → Archiv bildet die Pfade exakt ab (`Archiv\D\DZ-Test\…`).
- [ ] Archiv in einen OneDrive-/pCloud-Ordner legen → Warnung erscheint.
- [ ] USB-Stick als Archiv, während des Archivierens abziehen → Status „Warte auf Laufwerk …“, wieder einstecken → läuft weiter.
- [ ] Programm während des Archivierens über den Task-Manager beenden → Neustart fragt „an der Abbruchstelle fortsetzen“.
- [ ] **Archiv**-Fenster: einzelne Datei wiederherstellen, ganzen Lauf rückgängig.
- [ ] Original nach dem Archivieren ändern → **Archiv bereinigen** lässt die Kopie stehen.

## 4. Extras
- [ ] **Statistik** zeigt Balken je Kategorie.
- [ ] **Zeitplan** anlegen → Windows-Aufgabenplanung enthält „DateiZwilling Bericht“; „Jetzt ausführen“ → HTML-Bericht unter `Archiv\_DateiZwilling\Berichte`.
- [ ] Bericht exportieren mit „Pfade anonymisieren“ → kein Benutzername im Bericht.
- [ ] Sprache EN/DE, hoher Kontrast, Schriftgröße 150 %.
