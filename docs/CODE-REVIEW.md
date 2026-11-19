# DateiZwilling 2.0.0 – Code-Review

**Schwerpunkte:** Sicherheit · Stabilität · Ausfallsicherheit
**Datum:** 18.11.2026 · **Prüfer:** Claude (Anthropic)
**Umfang:** alle Module in `dateizwilling/`, `DateiZwilling.py`, Build-Skripte, 52 automatische Tests
(Die Funde R1–R13 aus Version 1.0/1.0.1 sind behoben und weiterhin durch Tests abgedeckt.)

## 1. Ergebnis in Kürze

| Bereich | Bewertung | Kernaussage |
|---|---|---|
| Datensicherheit | ✅ sehr gut | Kein Entfernen ohne verifizierte Kopie; vor dem endgültigen Löschen jetzt zusätzlich Byte-Vergleich Archivkopie ↔ Original (S1). |
| Ausfallsicherheit | ✅ sehr gut | Write-Ahead-Journal, Datenbank-Sicherung im Archiv (S4), Warten statt Fehler bei getrenntem Laufwerk (ST2), Anhalten bei vollem Speicher (S2), kein Standby (ST1). Praxistest `kill -9` während der Kopie erneut bestanden. |
| Sicherheit | ✅ gut | Keine Netzwerkzugriffe, keine Shell-Strings, SQL parametrisiert, HTML/CSV maskiert, Zip-Bomben-Grenze, XML ohne externe Entitäten, Diagnose und Berichte anonymisierbar. |
| Stabilität / Skalierung | ✅ gut | Dateiliste auf Festplatte (Millionen Dateien), Seitenansicht statt Anzeigegrenze, ein Vorschau-Thread mit Verwerfen veralteter Anfragen, wöchentliche Datenbankpflege. |
| Oberfläche | ⚠ eingeschränkt geprüft | Ablauf per Rauchtest mit Tk-Attrappe (inkl. Ordneransicht, Archiv-Browser, Statistik, Zeitplan); Darstellung bitte mit dem Testplan unter Windows prüfen. |

## 2. Umgesetzte Vorschläge 2.0

### Sicherheit
| # | Umsetzung | Test |
|---|---|---|
| S1 | `purge()` vergleicht Archivkopie und Original Byte für Byte (bei Textgruppen: Text-Fingerabdruck); bei Abweichung bleibt die Kopie | `test_s1_purge_compares_bytes` |
| S2 | Vorab-Prüfung je Ziellaufwerk (Bedarf + 1 % + 200 MB) und Prüfung je Datei; bei Platzmangel `NeedsAttention` – Lauf bleibt offen | `test_s2_not_enough_space_pauses_run` |
| S3 | FAT32: Dateien > 4 GB werden übersprungen; auf FAT/exFAT/NTFS werden ungültige Zeichen, Punkte/Leerzeichen am Ende und reservierte Namen ersetzt – Rückgängig stellt den Originalnamen wieder her | `test_s3_fat32_limit`, `test_s3_safe_names` |
| S4 | Nach jedem Lauf Sicherung der Datenbank (SQLite-Backup-API, atomar) nach `_DateiZwilling/DateiZwilling-Datenbank.sqlite`; „Archiv importieren“ liest die CSV-Protokolle und legt Läufe an | `test_s4_import_archive_into_new_database` |
| S5 | Einzelne Dateien wiederherstellen; Begleitdateien folgen automatisch | `test_s5_restore_single_file` |
| S6 | Warnung, wenn das Archiv in OneDrive/pCloud/Nextcloud/ownCloud/Dropbox/Google Drive/iCloud/Synology Drive/Box/MEGA liegt | `test_cloud_and_risky_detection` |
| S7 | Warnung bei Laufwerkswurzel, Benutzerordner, System-/Programmordnern als Quelle | dito |
| S8 | Erstellungsdatum und Attribute werden bei Kopien über Laufwerksgrenzen übernommen (Windows) | `copy_windows_metadata` |
| S9 | Versionsbereiche in `requirements.txt`, `build-lock.txt` mit exakten Ständen, SHA-256-Datei zur EXE/DMG, optionale Signatur (`DZ_SIGN_CERT`/`DZ_SIGN_PASS` bzw. `DZ_SIGN_ID`) | Build-Skripte |
| S10 | Berichte (HTML/CSV) und Diagnose-Export ohne Benutzername/Benutzerordner | `test_f6_stats_and_anonymized_report` |

### Stabilität
| # | Umsetzung |
|---|---|
| ST1 | `KeepAwake`: `SetThreadExecutionState` (Windows) bzw. `caffeinate` (macOS) während Scan/Archivierung |
| ST2 | Netz-/Gerätefehler oder nicht erreichbares Laufwerk → Status „Warte auf Laufwerk …“, automatisches Fortsetzen, jederzeit abbrechbar (`test_st2_*`) |
| ST3 | Ein Vorschau-Thread; veraltete Anfragen werden verworfen, Bilder erst im GUI-Thread übernommen |
| ST4 | `ScanTemp`: Dateiliste in temporärer SQLite-Datei; nur Kandidaten im Speicher; Ergebnisliste seitenweise (1000 Gruppen je Seite) |
| ST5 | SSD/HDD/Netz-Erkennung → 4/1/2 Lesevorgänge („0 = automatisch“) |
| ST6 | Wöchentlich: alte Sitzungen entfernen (letzte 10 bleiben), Cache-Obergrenze 3 Mio., `PRAGMA optimize`, `VACUUM` bei > 25 % freien Seiten; Schema-Migration 1 → 2 |
| ST7 | `docs/TESTPLAN.md` + „Diagnose exportieren“ (Protokolle anonymisiert, Systeminfo) |

## 3. Während des Reviews 2.0 gefundene und behobene Punkte

| # | Fund | Risiko | Behebung |
|---|---|---|---|
| R14 | Beim Archivieren doppelter Ordner wurden auch Kopien derselben Datei **außerhalb** der Ordner archiviert | unerwartetes Verschieben | Gruppen werden auf die Dateien der gewählten Ordner (+ Original) beschränkt (Test vorhanden) |
| R15 | Vorschau startete je Klick einen eigenen Thread | viele parallele Lesevorgänge | ein Worker-Thread, „neueste Anfrage gewinnt“ |
| R16 | `%` in Pfaden wäre in der Zeitplan-Datei als Variable gelesen worden | falscher Pfad | `%` → `%%` |
| R17 | Diagnose-Export hätte Protokolle mit vollständigen Pfaden enthalten | Datenschutz | Benutzerordner/-name werden ersetzt |
| R18 | Ergebnisliste alter Datenbanken unverträglich mit „nahezu gleich“-Gruppen | Fehler nach Update | Migration legt nur die Ergebnisliste neu an, Archiv-Journal bleibt |
| R19 | Kopfleiste mit sechs Knöpfen schob den Titel über die Knöpfe | Knöpfe abgeschnitten | Knöpfe zuerst platziert, Titel nimmt den Rest |
| R20 | Ressourcenleck beim Lesen von `/sys/block/*/rotational` | Dateihandle | `with open(...)` |

## 4. Sicherheitsprinzipien

1. **Verschieben statt Löschen**, atomar auf gleichem Laufwerk, sonst Kopie → `fsync` → Rücklesen + BLAKE2b → Umbenennen → Quelle entfernen.
2. **Zweifache Prüfung** beim Scan und vor dem Verschieben (Byte-Vergleich mit dem Original).
3. **Nie überschreiben** (`Name (DZ2).ext`).
4. **Freigabe vor dem Entfernen** mit Eingabe von LÖSCHEN plus Byte-Vergleich mit dem Original (S1).
5. **Geschützt:** System-/Papierkorbordner, App-Bibliotheken, Programm-Kataloge, Symlinks/Junctions, Hardlinks, Cloud-Platzhalter, geöffnete Office-Dokumente, geschützte Ordner, Ordnerregeln.
6. **Nahezu gleiche Dokumente** sind nicht bytegleich: eigene Ansicht, eigene Rückfrage, Text-Vergleich unmittelbar vor dem Verschieben und vor dem Bereinigen.
7. **Zeitplan** erzeugt nur Berichte – nie Verschieben oder Löschen.

## 5. Zustandsautomat je Datei

```
planned ──rename──────────────────────────────────────────► done
   │  └─ Laufwerk weg → warten ─┐
   │                            └─ wieder da → erneut versuchen
   └─(anderes Laufwerk)─► Platz? ─nein─► Lauf angehalten (bleibt offen)
                            │ja
                            ▼
                         copying ─verifiziert─► copied ─Quelle entfernt─► done
```

## 6. Tests

`python -m unittest discover -s tests` – **52 Tests**:

* `test_core.py` (29): Scan, Archiv, Pfadabbildung, Laufwerkswechsel, Rückgängig, Bereinigen, Schutzregeln, sechs Absturz-Szenarien, defekte Datenbank.
* `test_v2.py` (19): S1–S5, S10, ST2 (Warten + Abbruch während des Wartens), ST4, ST6, leere Ordner, doppelte Ordner, Ordnerregeln, Statistik, Zeitplan-Befehl, nahezu gleiche Dokumente, 3D-Kategorie und Vorschauen (STL, G-Code, RAW).
* `test_gui_smoke.py` (4): kompletter Oberflächenablauf, Wiederaufnahme der Sitzung, Ordneransicht mit Archivierung, dunkle Dialoge.

Praxistest: `kill -9` während einer Kopie auf ein anderes Dateisystem → `--cli resume` → alle 12 Dateien (480 MB) inhaltsgleich im Archiv, keine Reste, Datenbanksicherung im Archiv vorhanden.

## 7. Bekannte Grenzen

| Punkt | Erläuterung |
|---|---|
| Oberfläche | Nur mit Tk-Attrappe getestet – bitte `docs/TESTPLAN.md` unter Windows durchgehen. |
| Explorer-Miniaturen | Rückfall-Vorschau über die Windows-Shell ist ungetestet; bei Fehlern erscheint das Dateisymbol. |
| Drag & Drop | benötigt `tkinterdnd2` (wird vom Build installiert); ohne das Paket funktioniert alles außer Ziehen & Ablegen. |
| Video-Vorschau | benötigt `ffmpeg` im Suchpfad (optional). |
| macOS-Metadaten | Finder-Tags werden bei Kopien über Laufwerksgrenzen nicht übertragen (Umbenennen auf gleichem Laufwerk erhält alles). |
| Nahezu gleich | Nur für Formate mit zuverlässig auslesbarem Text (Word/Excel/PowerPoint, OpenDocument, PDF, Text/CSV/HTML). |
| Haftungsausschluss | Formulierung „soweit gesetzlich zulässig“; keine Rechtsberatung. |
