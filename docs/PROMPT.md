# DateiZwilling – Original-Prompt

**Idee und Konzept:** Stefan J. Kaiser DM5CQ / OE8KKS
**Umsetzung:** Claude (Anthropic), 18.11.2026
**Version:** 1.0.1

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
| A13 | Alles als ZIP | `DateiZwilling-1.0.1.zip` |

## Nachtrag 1.0.1

> und über das INFO ist die Menüzeile in Weiss dargesteltl es soll alles in Dunkelgrau mit wiesserschrift und orangen akzenten dargestellt werden. - Die PDF Dukomente fehlen noch. die Fenster und Programmdatei passen nicht immer - es muss zuerst auf Vollbild gegangen werden damit der Starte Scan Button erscheint. dass sollte alles sichtbar sien - oder dynamisch skaliert. ggf. damit es gut aussiehe. Die Weissen Checkboxen sollten grau mit weiss oder orange sein

