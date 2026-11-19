from PIL import Image, ImageDraw, ImageFont
import sys
lang = sys.argv[2]
W, H = 1600, 1000
im = Image.new("RGB", (W, H), "#2b2b2b"); d = ImageDraw.Draw(im)
sys.path.insert(0, sys.argv[4]) if len(sys.argv) > 4 else None
import math
from dateizwilling.preview import render_mesh
def _halter():
    tris = []
    def box(x0, y0, z0, x1, y1, z1):
        v = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
        for f in [(0,1,2),(0,2,3),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]:
            tris.append(tuple(v[k] for k in f))
    box(-30, -10, 0, 30, 10, 5); box(-30, -10, 0, -24, 10, 40)
    n = 32
    for j in range(n):
        a0, a1 = 2*math.pi*j/n, 2*math.pi*(j+1)/n
        p = lambda a, z: (10 + 7*math.cos(a), 7*math.sin(a), z)
        tris.append((p(a0, 5), p(a1, 5), p(a1, 55))); tris.append((p(a0, 5), p(a1, 55), p(a0, 55)))
        tris.append(((10, 0, 55), p(a0, 55), p(a1, 55)))
    return tris
STL = render_mesh(_halter(), (100, 78)).resize((200, 155))
F = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
OR, FG, MU, PAN, FIELD = "#f28c28", "#f0f0f0", "#a8a8a8", "#333333", "#3c3c3c"
de = lang == "de"
# Titelleiste + Kopf
d.rectangle((0, 0, W, 34), fill="#3a3a3a"); d.text((14, 8), "DateiZwilling 2.0.0", fill=FG, font=F(16))
d.rectangle((0, 34, W, 120), fill="#232323")
icon = Image.open(sys.argv[3]).convert("RGBA").resize((64, 64)); im.paste(icon, (20, 45), icon)
d.text((100, 48), "DateiZwilling", fill=OR, font=F(30, True))
d.text((100, 88), "Inhaltsgleiche Dateien finden & sicher archivieren" if de else "Find identical files & archive them safely", fill=MU, font=F(16))
hb = ["Info", "⚙ " + ("Einstellungen" if de else "Settings"), "◷ " + ("Zeitplan" if de else "Schedule"),
      "▥ " + ("Statistik" if de else "Statistics"), "▤ " + ("Archiv" if de else "Archive"), "EN" if de else "DE"]
x1 = W - 20
for t in hb:
    tw = int(d.textlength(t, font=F(15))) + 26
    d.rounded_rectangle((x1 - tw, 62, x1, 98), 6, fill="#2f2f2f"); d.text((x1 - tw + 13, 71), t, fill=FG, font=F(15))
    x1 -= tw + 8
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
cats = ["Office", "PDF", "Bilder", "RAW", "Adobe", "Affinity", "Capture One", "3D-Druck & CAD", "Video", "Audio", "Text", "Sonstige"] if de else ["Office", "PDF", "Images", "RAW", "Adobe", "Affinity", "Capture One", "3D print & CAD", "Video", "Audio", "Text", "Other"]
for i, c in enumerate(cats):
    x = 18 + (i % 2) * 180; yy = y + (i // 2) * 26
    d.rectangle((x, yy+3, x+14, yy+17), fill=OR); d.text((x+22, yy), c, fill=FG, font=F(14))
y += 165
sec("Original behalten" if de else "Keep as original"); box(32)
d.rounded_rectangle((18, H-185, 382, H-135), 6, fill=OR); d.text((90, H-175), "▶  Scan starten  (F5)" if de else "▶  Start scan  (F5)", fill="#1e1e1e", font=F(20, True))
d.rounded_rectangle((18, H-125, 195, H-90), 5, fill=FIELD); d.text((80, H-118), "Pause", fill=FG, font=F(15))
d.rounded_rectangle((205, H-125, 382, H-90), 5, fill=FIELD); d.text((235, H-118), "■ " + ("Abbrechen" if de else "Cancel"), fill="#d9534f", font=F(15))
# Hauptbereich: Filter
d.text((420, 135), ("Suche:" if de else "Search:"), fill=FG, font=F(15)); d.rectangle((490, 132, 720, 160), fill=FIELD)
d.text((740, 135), ("Kategorie:" if de else "Category:"), fill=FG, font=F(15)); d.rectangle((830, 132, 990, 160), fill=FIELD)
d.text((1010, 135), ("Sortierung:" if de else "Sort:"), fill=FG, font=F(15)); d.rectangle((1110, 132, 1300, 160), fill=FIELD)
# Ansicht + Seiten
d.text((420, 175), ("Ansicht:" if de else "View:"), fill=FG, font=F(15)); d.rectangle((500, 172, 760, 198), fill=FIELD)
d.text((508, 175), ("Identische Dateien  ▾" if de else "Identical files  ▾"), fill=FG, font=F(14))
d.text((780, 175), ("◀  Seite 1/3  ▶" if de else "◀  Page 1/3  ▶"), fill=FG, font=F(15))
d.text((W-330, 175), "1.284 · 2.917 ⇢ · 38,6 GB", fill=OR, font=F(15))
# Liste
d.rectangle((420, 210, W-20, 560), fill=FIELD)
d.rectangle((420, 210, W-20, 238), fill=PAN)
for x, t in [(430, "Datei" if de else "File"), (760, "Ordner" if de else "Folder"), (1180, "Größe" if de else "Size"), (1290, "Geändert" if de else "Modified"), (1450, "Aktion" if de else "Action")]:
    d.text((x, 215), t, fill=FG, font=F(15, True))
rows = [("g", "Gruppe 1 · 2 Dateien · 2,4 MB · Ersparnis 2,4 MB · 3D-Druck & CAD" if de else "Group 1 · 2 files · 2.4 MB · savings 2.4 MB · 3D printing & CAD"),
        ("k", "Antennenhalter_v3.stl", "D:\\3D-Druck\\Funk", "★ behalten" if de else "★ keep", "2,4 MB"),
        ("d", "Antennenhalter_v3 (1).stl", "C:\\Users\\Stefan\\Downloads", "⇢ archivieren" if de else "⇢ archive", "2,4 MB"),
        ("g", "Gruppe 2 · 3 Dateien · 48,2 MB · Ersparnis 96,4 MB · Office" if de else "Group 2 · 3 files · 48.2 MB · savings 96.4 MB · Office"),
        ("k", "Angebot 2024.pptx", "D:\\Dokumente\\Kunden", "★ behalten" if de else "★ keep", "48,2 MB"),
        ("d", "Angebot 2024 (Kopie).pptx", "E:\\Sicherung 2023\\Kunden", "⇢ archivieren" if de else "⇢ archive", "48,2 MB"),
        ("g", "Gruppe 3 · 2 Dateien · 31,0 MB · Ersparnis 31,0 MB · Kamera-RAW" if de else "Group 3 · 2 files · 31.0 MB · savings 31.0 MB · Camera RAW")]
yy = 245
for r in rows:
    if r[0] == "g":
        d.rectangle((420, yy, W-20, yy+38), fill="#353535"); d.text((432, yy+9), "▾ " + r[1], fill=OR, font=F(15, True))
    else:
        col = "#5cb85c" if r[0] == "k" else FG
        if r is rows[2]:
            d.rectangle((420, yy, W-20, yy+38), fill=OR); col = "#1e1e1e"
        d.text((458, yy+9), r[1], fill=col, font=F(15)); d.text((760, yy+9), r[2], fill=col, font=F(15))
        d.text((1180, yy+9), r[4], fill=col, font=F(15)); d.text((1290, yy+9), "12.03.2024", fill=col, font=F(15)); d.text((1450, yy+9), r[3], fill=col, font=F(15))
    yy += 43
# Vergleich
for i, (t, c) in enumerate([("Original (bleibt)" if de else "Original (kept)", "#5cb85c"), ("Duplikat (wird archiviert)" if de else "Duplicate (will be archived)", "#f0ad4e")]):
    x0 = 420 + i * 590
    d.rectangle((x0, 575, x0 + 575, 830), fill=PAN, outline="#4a4a4a"); d.text((x0+12, 583), t, fill=c, font=F(16, True))
    d.rectangle((x0+12, 615, x0+212, 770), fill=FIELD); im.paste(STL, (x0+12, 615))
    for k, line in enumerate(["Antennenhalter_v3.stl" if i == 0 else "Antennenhalter_v3 (1).stl", ("Pfad: " if de else "Path: ") + ("D:\\3D-Druck\\Funk" if i == 0 else "C:\\Users\\Stefan\\Downloads"), ("Größe: 2,4 MB" if de else "Size: 2.4 MB"), ("Typ: 3D-Druck & CAD (.stl)" if de else "Type: 3D printing & CAD (.stl)"), ("Prüfsumme: 9f3a1c…" if de else "Checksum: 9f3a1c…")]):
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
marks = [(370, 140, 1), (370, 395, 2), (370, 555, 3), (200, H-205, 4), (1320, 140, 5), (1560, 215, 6), (1560, 590, 7), (960, 905, 8), (1585, 845, 9), (345, H-68, 10), (940, 80, 11)]
for x, y0, n in marks:
    d.ellipse((x-17, y0-17, x+17, y0+17), fill="#5bc0de", outline="#ffffff", width=2)
    d.text((x - (6 if n < 10 else 11), y0-11), str(n), fill="#000000", font=F(18, True))
im.save(sys.argv[1], optimize=True)
