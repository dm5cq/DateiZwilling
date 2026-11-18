from PIL import Image, ImageDraw, ImageFilter
import sys, os
out = sys.argv[1]
S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((40, 40, S-40, S-40), radius=200, fill=(43, 43, 43, 255), outline=(70, 70, 70, 255), width=12)
def sheet(x, y, w, h, fill, fold):
    pts = [(x, y), (x+w-fold, y), (x+w, y+fold), (x+w, y+h), (x, y+h)]
    sh = Image.new("RGBA", (S, S), (0,0,0,0)); sd = ImageDraw.Draw(sh)
    sd.polygon([(px+14, py+18) for px, py in pts], fill=(0,0,0,120))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(sh)
    d.polygon(pts, fill=fill)
    d.polygon([(x+w-fold, y), (x+w-fold, y+fold), (x+w, y+fold)], fill=tuple(max(0, c-45) for c in fill[:3]) + (255,))
# hinteres Blatt (grau) und vorderes Blatt (orange)
sheet(190, 190, 420, 540, (150, 150, 150, 255), 110)
sheet(400, 300, 440, 560, (242, 140, 40, 255), 120)
# Textzeilen auf dem grauen Blatt
for i in range(4):
    d.rounded_rectangle((235, 350 + i*70, 360, 375 + i*70), radius=12, fill=(110, 110, 110, 255))
# Gleichheitszeichen auf dem orangen Blatt
d.rounded_rectangle((505, 520, 735, 570), radius=22, fill=(255, 255, 255, 255))
d.rounded_rectangle((505, 625, 735, 675), radius=22, fill=(255, 255, 255, 255))
img.save(os.path.join(out, "icon_1024.png"))
img.resize((256, 256), Image.LANCZOS).save(os.path.join(out, "icon.png"))
img.resize((96, 96), Image.LANCZOS).save(os.path.join(out, "icon_96.png"))
img.resize((48, 48), Image.LANCZOS).save(os.path.join(out, "icon_48.png"))
img.save(os.path.join(out, "icon.ico"), sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
try:
    img.save(os.path.join(out, "icon.icns"))
    print("icns ok")
except Exception as e:
    print("icns fail", e)
