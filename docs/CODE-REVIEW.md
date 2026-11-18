# DateiZwilling 1.0.0 – Code-Review

**Schwerpunkte:** Sicherheit · Stabilität · Ausfallsicherheit
**Datum:** 18.11.2026 · **Prüfer:** Claude (Anthropic)
**Umfang:** `dateizwilling/*.py`, `DateiZwilling.py`, Build-Skripte

## 1. Ergebnis in Kürze

| Bereich | Bewertung | Kernaussage |
|---|---|---|
| Datensicherheit (kein Datenverlust) | ✅ gut | Keine Datei wird entfernt, bevor eine verifizierte Kopie existiert; das behaltene Original wird vor jedem Schritt erneut geprüft. |
| Ausfallsicherheit / Fortsetzen | ✅ gut | Write-Ahead-Journal; Absturz per `kill -9` mitten im Kopieren getestet – Lauf wurde nach Neustart vollständig und inhaltsgleich beendet. |
| Sicherheit (Angriffsfläche) | ✅ gut | Kein Netzwerkzugriff, keine Shell-Strings aus Dateinamen, SQL nur parametrisiert, HTML/CSV-Ausgaben maskiert. |
| Stabilität | ✅ gut | Fehler einzelner Dateien stoppen den Lauf nicht; Abbruch/Pause jederzeit; Datenbank-Selbstprüfung beim Start. |
| Oberfläche | ⚠ eingeschränkt geprüft | Ablauf über Rauchtest mit Tk-Attrappe geprüft; Darstellung muss unter Windows/macOS real angesehen werden. |

## 2. Während des Reviews gefundene und behobene Punkte

| # | Fund | Risiko | Behebung |
|---|---|---|---|
| R1 | Zeitstempel aus Verzeichniseinträgen (scandir) können auf Netzlaufwerken von `os.stat` abweichen → alle Dateien würden als „geändert“ verworfen | Duplikate auf NAS nicht gefunden | Kandidaten erhalten Zeitstempel/Größe aus `os.stat`; Größenänderung → Datei wird übersprungen |
| R2 | Archivlaufwerk (USB) beim Neustart nicht verbunden → Wiederherstellung hätte Schritte fälschlich als „Quelle fehlt“ markiert | Verlust der Rückgängig-Information | Wiederherstellung und Fortsetzen werden verschoben, bis das Archiv erreichbar ist (Test vorhanden) |
| R3 | Geöffnete Office-Dokumente könnten auf macOS/SMB verschoben werden | Datenverlust beim Speichern im Programm | Sperrdateien `~$…` und `.~lock.…#` werden erkannt → Datei wird übersprungen (Test vorhanden) |
| R4 | Cache-Logik: Schnell- und Voll-Prüfsumme konnten bei großen Dateien vermischt werden | übersehene Duplikate | Getrennte Behandlung kleiner/großer Dateien im Cache |
| R5 | CSV-/Formel-Injektion (Dateiname beginnt mit `=`) beim Öffnen von Bericht/Manifest in Excel | Ausführung von Formeln | `csv_safe()` maskiert solche Werte |
| R6 | Leck einer SQLite-Verbindung bei beschädigter Datenbank | Ressourcenleck | Verbindung wird bei Fehler geschlossen; defekte DB wird gesichert und neu angelegt |
| R7 | Emoji außerhalb der Unicode-Grundebene in Schaltflächen | Darstellungsfehler unter Tk 8.6 | durch BMP-Symbole ersetzt |
| R8 | Hoher Speicherbedarf bei Millionen Dateien | Absturz bei sehr großen Laufwerken | `FileRec` mit `__slots__` (≈ 40 % weniger Speicher) |
| R9 | Fortschrittsanzeige beim Archivieren lief über 100 % (Verifikations-Lesevorgänge) | Irreführende Anzeige | Archiv-Fortschritt nach Dateien statt Bytes |

## 3. Sicherheitsprinzipien im Code

1. **Verschieben statt Löschen.** Gleiches Laufwerk: atomares `rename`. Anderes Laufwerk: Kopie in `*.dzpart` → `fsync` → Rücklesen + BLAKE2b-Vergleich → Umbenennen → erst dann Quelle entfernen. Lässt sich die Quelle nicht entfernen, wird die Kopie wieder gelöscht (kein Doppelzustand).
2. **Zweifache Prüfung.** Scan: Größe + Schnell-Prüfsumme + BLAKE2b-256. Vor dem Verschieben (Standard): Byte-für-Byte-Vergleich mit dem behaltenen Original. Fehlt das Original oder weicht es ab, bleibt das Duplikat unangetastet.
3. **Nie überschreiben.** Ist der Zielpfad im Archiv belegt, wird `Name (DZ2).ext` verwendet.
4. **Freigabe vor dem Entfernen.** „Archiv bereinigen“ verlangt Auswahl der Läufe und Eingabe von LÖSCHEN; entfernt wird nur, wenn das Original in diesem Moment noch existiert. Netzlaufwerke werden erkannt (kein Papierkorb → deutlicher Hinweis).
5. **Geschützte Bereiche.** System-/Papierkorbordner, App-Pakete und Bibliotheken (`.photoslibrary`, `.lrdata`, `.cocatalog`, `.fcpbundle` …), Programm-Kataloge (`.lrcat`, `.cocatalogdb`, `.pst` …), Symlinks/Junctions, Hardlinks, Cloud-Platzhalter und frei wählbare geschützte Ordner.
6. **Begleitdateien.** XMP/COS/AAE/PP3 wandern mit dem Duplikat; eine nur über den Stamm zugeordnete XMP bleibt, wenn eine andere Datei gleichen Namens (RAW+JPEG) im Ordner bleibt.
7. **Einzelinstanz.** Sperrdatei verhindert zwei gleichzeitige Instanzen auf derselben Datenbank.

## 4. Ausfallsicherheit – Zustandsautomat je Datei

```
planned ──rename──────────────────────────────► done
   │
   └─(anderes Laufwerk)─► copying ─verifiziert─► copied ─Quelle entfernt─► done
                              │                     │
                        Absturz: tmp löschen,  Absturz: Ziel prüfen,
                        zurück auf planned     Quelle entfernen → done
```

* Jeder Zustand wird **vor** der Aktion in SQLite (WAL, `synchronous=FULL`) geschrieben.
* Beim Start repariert `recover_all()` halbfertige Schritte; danach fragt die App, ob der Lauf an der Abbruchstelle fortgesetzt werden soll.
* Scan: Prüfsummen werden spätestens alle 2 s in den Cache geschrieben – ein erneuter Scan liest bereits geprüfte Dateien nicht noch einmal.
* Zusätzlich liegt im Archiv unter `_DateiZwilling/` je Lauf ein CSV-Manifest (Originalpfad, Archivpfad, Original, Prüfsumme) – selbst ohne Datenbank ist alles nachvollziehbar.

## 5. Automatische Tests (`python -m unittest discover -s tests`)

* **Scan:** Gruppenbildung, scheinbar gleiche Dateien (gleiche Größe, gleicher Anfang/Ende), leere Dateien, Office-Sperrdateien, Hardlinks, Symlinks, Archiv im Quellordner, verschachtelte Quellordner, Kategorien, geschützte Ordner, Regel „neueste“, Änderung während des Scans, Fortsetzen nach Abbruch mit Cache.
* **Archiv:** exakte Pfadabbildung, Nur-Prüfsummen-Modus, Laufwerkswechsel (Kopie + Verifikation), Original geändert/gelöscht, nie überschreiben, Rückgängig, Bereinigen nur mit vorhandenem Original, Abbruch, geöffnete Dokumente, Archivlaufwerk offline.
* **Absturz-Simulation:** vor dem ersten Schritt, nach Umbenennen vor Journal-Eintrag, während der Kopie, nach Kopie vor Löschen, defekte Kopie im Archiv, Ausnahme mitten im Lauf.
* **Datenbank:** beschädigte Datenbank wird erkannt, gesichert und ersetzt.
* **Oberfläche:** Rauchtest kompletter Ablauf (Scan → Auswahl → Original festlegen → Archivieren → Sprache → Dialoge → Rückgängig) und Wiederaufnahme der letzten Sitzung.
* **Praxis-Test:** `kill -9` während des Kopierens auf ein anderes Dateisystem → Neustart → `resume`: alle 12 Dateien (480 MB) inhaltsgleich im Archiv, keine `.dzpart`-Reste.

## 6. Verbleibende Hinweise / bekannte Grenzen

| Punkt | Erläuterung | Empfehlung |
|---|---|---|
| Oberfläche nicht auf echtem Bildschirm getestet | Die Testumgebung hat keine Tk-Anzeige; Logik ist getestet, Optik nicht | Erster Start unter Windows ansehen und Auffälligkeiten melden |
| BildZwilling-Code nicht verfügbar | Das GitHub-Repository `dm5cq/BildZwilling` enthielt nur die Lizenz; der Stil wurde nach den bekannten Vorgaben nachgebaut | Bei Abweichungen Screenshot von BildZwilling schicken |
| Kopie über Laufwerksgrenzen | Änderungsdatum und Rechte bleiben erhalten; Erstellungsdatum (Windows), NTFS-Alternate-Data-Streams und macOS-Finder-Tags nicht | Archiv möglichst auf dasselbe Laufwerk legen (dann atomares Umbenennen, alles bleibt erhalten) |
| POSIX `rename` überschreibt | Zwischen Prüfung und Umbenennen könnte theoretisch eine Datei entstehen | durch Einzelinstanz-Sperre praktisch ausgeschlossen |
| Papierkorb auf Netzlaufwerken | Windows/macOS haben dort keinen Papierkorb | App erkennt das und erlaubt nur bewusstes endgültiges Löschen |
| Unsignierte EXE | Windows SmartScreen warnt beim ersten Start | „Weitere Informationen → Trotzdem ausführen“ oder eigene Signatur |
| macOS-Datenschutz | Zugriff auf Schreibtisch/Dokumente/externe Laufwerke muss erlaubt werden | Systemeinstellungen → Datenschutz → Festplattenvollzugriff |
