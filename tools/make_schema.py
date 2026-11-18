from PIL import Image, ImageDraw, ImageFont
import sys
lang = sys.argv[2]
W, H = 1600, 1000
im = Image.new("RGB", (W, H), "#2b2b2b"); d = ImageDraw.Draw(im)
F = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
OR, FG, MU, PAN, FIELD = "#f28c28", "#f0f0f0", "#a8a8a8", "#333333", "#3c3c3c"
de = lang == "de"
# Titelleiste + Kopf
d.rectangle((0, 0, W, 34), fill="#3a3a3a"); d.text((14, 8), "DateiZwilling 1.0.0", fill=FG, font=F(16))
d.rectangle((0, 34, W, 120), fill="#232323")
icon = Image.open(sys.argv[3]).convert("RGBA").resize((64, 64)); im.paste(icon, (20, 45), icon)
d.text((100, 48), "DateiZwilling", fill=OR, font=F(30, True))
d.text((100, 88), "Inhaltsgleiche Dateien finden & sicher archivieren" if de else "Find identical files & archive them safely", fill=MU, font=F(16))
for i, t in enumerate(["Info", "⚙ " + ("Einstellungen" if de else "Settings"), "EN" if de else "DE"]):
    d.rounded_rectangle((W-140-i*170, 62, W-20-i*170, 98), 6, fill="#2f2f2f"); d.text((W-125-i*170, 70), t, fill=FG, font=F(16))
# Seitenleiste
d.rectangle((0, 120, 400, H-50), fill=PAN)
y = 135
def sec(t):
    global y; d.text((18, y), t, fill=OR, font=F(16, True)); y += 28
def box(h):
    global y; d.rectangle((18, y, 382, y+h), fill=FIELD, outline="#4a4a4a"); y += h + 10
sec("Quellordner (Priorität)" if de else "Source folders (priority)")
d.rectangle((18, y, 382, y+90), fill=FIELD, outline="#4a4a4a")
for i, p in enumerate(["D:\\Dokumente", "E:\\Sicherung 2023", "\\\\NAS\\daten"]):
    d.text((26, y+6+i*27), p, fill=FG, font=F(14))
y += 100
for i, t in enumerate(["+", "–", "↑", "↓"]):
    d.rounded_rectangle((18+i*60, y, 70+i*60, y+30), 5, fill=FIELD); d.text((36+i*60, y+5), t, fill=FG, font=F(16))
y += 45
sec("Archivordner" if de else "Archive folder"); box(32)
sec("Geschützte Ordner" if de else "Protected folders"); box(55)
sec("Dateitypen" if de else "File types")
cats = ["Office", "PDF", "Bilder", "RAW", "Adobe", "Affinity", "Capture One", "Video", "Audio", "Text"] if de else ["Office", "PDF", "Images", "RAW", "Adobe", "Affinity", "Capture One", "Video", "Audio", "Text"]
for i, c in enumerate(cats):
    x = 18 + (i % 2) * 180; yy = y + (i // 2) * 26
    d.rectangle((x, yy+3, x+14, yy+17), fill=OR); d.text((x+22, yy), c, fill=FG, font=F(14))
y += 140
sec("Original behalten" if de else "Keep as original"); box(32)
d.rounded_rectangle((18, H-185, 382, H-135), 6, fill=OR); d.text((90, H-175), "▶  Scan starten  (F5)" if de else "▶  Start scan  (F5)", fill="#1e1e1e", font=F(20, True))
d.rounded_rectangle((18, H-125, 195, H-90), 5, fill=FIELD); d.text((80, H-118), "Pause", fill=FG, font=F(15))
d.rounded_rectangle((205, H-125, 382, H-90), 5, fill=FIELD); d.text((235, H-118), "■ " + ("Abbrechen" if de else "Cancel"), fill="#d9534f", font=F(15))
# Hauptbereich: Filter
d.text((420, 135), ("Suche:" if de else "Search:"), fill=FG, font=F(15)); d.rectangle((490, 132, 720, 160), fill=FIELD)
d.text((740, 135), ("Kategorie:" if de else "Category:"), fill=FG, font=F(15)); d.rectangle((830, 132, 990, 160), fill=FIELD)
d.text((1010, 135), ("Sortierung:" if de else "Sort:"), fill=FG, font=F(15)); d.rectangle((1110, 132, 1300, 160), fill=FIELD)
# Liste
d.rectangle((420, 175, W-20, 560), fill=FIELD)
d.rectangle((420, 175, W-20, 203), fill=PAN)
for x, t in [(430, "Datei" if de else "File"), (760, "Ordner" if de else "Folder"), (1180, "Größe" if de else "Size"), (1290, "Geändert" if de else "Modified"), (1450, "Aktion" if de else "Action")]:
    d.text((x, 180), t, fill=FG, font=F(15, True))
rows = [("g", "Gruppe 1 · 3 Dateien · 48,2 MB · Ersparnis 96,4 MB · Office" if de else "Group 1 · 3 files · 48.2 MB · savings 96.4 MB · Office"),
        ("k", "Angebot 2024.pptx", "D:\\Dokumente\\Kunden", "★ behalten" if de else "★ keep"),
        ("d", "Angebot 2024 (Kopie).pptx", "E:\\Sicherung 2023\\Kunden", "⇢ archivieren" if de else "⇢ archive"),
        ("d", "Praesentation final.pptx", "\\\\NAS\\daten\\alt", "⇢ archivieren" if de else "⇢ archive"),
        ("g", "Gruppe 2 · 2 Dateien · 31,0 MB · Ersparnis 31,0 MB · Kamera-RAW" if de else "Group 2 · 2 files · 31.0 MB · savings 31.0 MB · Camera RAW"),
        ("k", "DSCF1234.RAF", "D:\\Fotos\\2024\\Juni", "★ behalten" if de else "★ keep"),
        ("d", "DSCF1234.RAF", "E:\\Sicherung 2023\\Import", "⇢ archivieren" if de else "⇢ archive"),
        ("g", "Gruppe 3 · 2 Dateien · 12,7 MB · Ersparnis 12,7 MB · Affinity" if de else "Group 3 · 2 files · 12.7 MB · savings 12.7 MB · Affinity")]
yy = 210
for r in rows:
    if r[0] == "g":
        d.rectangle((420, yy, W-20, yy+38), fill="#353535"); d.text((432, yy+9), "▾ " + r[1], fill=OR, font=F(15, True))
    else:
        col = "#5cb85c" if r[0] == "k" else FG
        if r is rows[2]:
            d.rectangle((420, yy, W-20, yy+38), fill=OR); col = "#1e1e1e"
        d.text((458, yy+9), r[1], fill=col, font=F(15)); d.text((760, yy+9), r[2], fill=col, font=F(15))
        d.text((1180, yy+9), "48,2 MB" if yy < 400 else "31,0 MB", fill=col, font=F(15)); d.text((1290, yy+9), "12.03.2024", fill=col, font=F(15)); d.text((1450, yy+9), r[3], fill=col, font=F(15))
    yy += 43
# Vergleich
for i, (t, c) in enumerate([("Original (bleibt)" if de else "Original (kept)", "#5cb85c"), ("Duplikat (wird archiviert)" if de else "Duplicate (will be archived)", "#f0ad4e")]):
    x0 = 420 + i * 590
    d.rectangle((x0, 575, x0 + 575, 830), fill=PAN, outline="#4a4a4a"); d.text((x0+12, 583), t, fill=c, font=F(16, True))
    d.rectangle((x0+12, 615, x0+212, 770), fill=FIELD); d.rectangle((x0+82, 650, x0+142, 730), outline=OR, width=3); d.text((x0+90, 680), ".PPTX", fill=FG, font=F(13, True))
    for k, line in enumerate(["Angebot 2024.pptx" if i == 0 else "Angebot 2024 (Kopie).pptx", ("Pfad: " if de else "Path: ") + ("D:\\Dokumente\\Kunden" if i == 0 else "E:\\Sicherung 2023\\Kunden"), ("Größe: 48,2 MB" if de else "Size: 48.2 MB"), ("Prüfsumme: 9f3a1c…" if de else "Checksum: 9f3a1c…")]):
        d.text((x0+230, 620 + k*30), line, fill=FG, font=F(14))
    d.rounded_rectangle((x0+12, 785, x0+110, 818), 5, fill=FIELD); d.text((x0+28, 792), "Öffnen" if de else "Open", fill=FG, font=F(14))
    d.rounded_rectangle((x0+120, 785, x0+290, 818), 5, fill=FIELD); d.text((x0+132, 792), "Im Ordner zeigen" if de else "Show in folder", fill=FG, font=F(14))
# Aktionsleisten
d.rounded_rectangle((420, 845, 740, 880), 5, fill=FIELD); d.text((432, 852), "★ Als Original festlegen (Enter)" if de else "★ Set as original (Enter)", fill=FG, font=F(14))
d.rounded_rectangle((1060, 845, 1340, 880), 5, fill=FIELD); d.text((1072, 852), "↶ Letzte Archivierung rückgängig" if de else "↶ Undo last archiving", fill=FG, font=F(14))
d.rounded_rectangle((1350, 845, W-20, 880), 5, fill=FIELD); d.text((1362, 852), "Archiv bereinigen …" if de else "Clean up archive …", fill="#d9534f", font=F(14))
d.rounded_rectangle((420, 892, 640, 930), 5, fill=FIELD); d.text((432, 900), "⇢ Auswahl archivieren" if de else "⇢ Archive selection", fill=FG, font=F(14))
d.rounded_rectangle((650, 892, 950, 930), 5, fill=OR); d.text((662, 900), "⇢ Alle Duplikate archivieren" if de else "⇢ Archive all duplicates", fill="#1e1e1e", font=F(14, True))
# Statusleiste
d.rectangle((0, H-50, W, H), fill="#232323"); d.rectangle((14, H-35, 334, H-17), fill=FIELD); d.rectangle((14, H-35, 250, H-17), fill=OR)
d.text((350, H-37), ("Vollständige Prüfsumme 812/1024  ·  640 aus Cache" if de else "Full checksum 812/1024  ·  640 from cache"), fill=FG, font=F(15))
d.text((W-330, H-37), "412 MB/s   ≈ 0:42", fill=MU, font=F(15)); d.text((W-120, H-37), ("Protokoll ▴" if de else "Log ▴"), fill=FG, font=F(15))
# Nummern
marks = [(370, 140, 1), (370, 395, 2), (370, 555, 3), (200, H-205, 4), (1320, 140, 5), (1560, 215, 6), (1560, 590, 7), (960, 905, 8), (1585, 845, 9), (345, H-68, 10)]
for x, y0, n in marks:
    d.ellipse((x-17, y0-17, x+17, y0+17), fill="#5bc0de", outline="#ffffff", width=2)
    d.text((x - (6 if n < 10 else 11), y0-11), str(n), fill="#000000", font=F(18, True))
im.save(sys.argv[1], optimize=True)
