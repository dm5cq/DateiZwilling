"""Vorschaubilder fuer die Vergleichsansicht (F1).

Liefert ein PIL-Bild oder None. Laeuft im Hintergrund-Thread; jede Quelle ist
optional und faellt bei Fehlern still auf die naechste zurueck:

* Bilder (Pillow), PSD-Gesamtbild
* RAW: eingebettetes JPEG-Vorschaubild
* PDF: erste Seite (pypdfium2, optional)
* Office/OpenDocument/iWork/3MF: eingebettetes Vorschaubild im ZIP-Container
* G-Code (PrusaSlicer, OrcaSlicer, Bambu, Cura-Plugins): eingebettete Vorschau
* STL/OBJ: eigene schattierte Darstellung des 3D-Modells
* Video: Standbild (ffmpeg, falls installiert)
* Rueckfall: Windows-Explorer-Miniatur bzw. macOS Quick Look
"""
from __future__ import annotations

import base64
import io
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile

from .formats import CATEGORIES, PREVIEWABLE, ext_of
from .pathutil import IS_MAC, IS_WIN, fs

try:
    from PIL import Image, ImageDraw, ImageOps  # type: ignore
except Exception:  # pragma: no cover
    Image = ImageDraw = ImageOps = None  # type: ignore

MAX_IMAGE_FILE = 200 * 1024 * 1024
RAW_SCAN = 48 * 1024 * 1024
ZIP_THUMBS = [
    r"docProps/thumbnail\.(jpeg|jpg|png)", r"Thumbnails/thumbnail\.png", r"preview\.jpg",
    r"QuickLook/Thumbnail\.(jpg|png)", r"preview-web\.jpg", r"Metadata/thumbnail\.png",
    r"Metadata/plate_1\.png", r"Metadata/top_1\.png", r"Auxiliaries/\.thumbnails/thumbnail_middle\.png",
    r"Auxiliaries/\.thumbnails/thumbnail_3mf\.png", r"Metadata/.*thumbnail.*\.png",
]
ZIP_EXTS = {"docx", "docm", "dotx", "xlsx", "xlsm", "xltx", "pptx", "pptm", "ppsx", "potx", "vsdx",
            "odt", "ods", "odp", "odg", "ott", "ots", "otp", "pages", "numbers", "key", "3mf", "xps",
            "oxps", "epub", "idml", "afdesign", "afphoto", "afpub", "af", "ufp"}
VIDEO_EXTS = CATEGORIES.get("video", set())
RAW_EXTS = CATEGORIES.get("raw", set())


def make_preview(path: str, box: tuple[int, int] = (360, 260)) -> "Image.Image | None":
    if Image is None:
        return None
    ext = ext_of(path)
    try:
        size = os.path.getsize(fs(path))
    except OSError:
        return None
    steps = []
    if ext in PREVIEWABLE or ext in ("psd", "webp", "tif", "tiff"):
        steps.append(_image)
    if ext in RAW_EXTS or ext in ("dng", "tif"):
        steps.append(_raw_embedded)
    if ext == "pdf":
        steps.append(_pdf)
    if ext in ZIP_EXTS:
        steps.append(_zip_thumb)
    if ext in ("gcode", "gco", "g", "bgcode"):
        steps.append(_gcode_thumb)
    if ext == "stl":
        steps.append(_stl)
    if ext == "obj":
        steps.append(_obj)
    if ext in VIDEO_EXTS or ext in ("insv", "lrv"):
        steps.append(_video)
    steps.append(_system_thumb)
    for step in steps:
        try:
            img = step(path, size, box)
        except Exception:
            img = None
        if img is not None:
            img = img.convert("RGB")
            img.thumbnail(box)
            return img
    return None


# --------------------------------------------------------------- Bilder
def _image(path, size, box):
    if size > MAX_IMAGE_FILE:
        return None
    im = Image.open(fs(path))
    im.draft("RGB", (box[0] * 2, box[1] * 2))
    im = ImageOps.exif_transpose(im)
    im.load()
    return im


def _raw_embedded(path, size, box):
    """Groesstes dekodierbares JPEG im RAW-Container (ohne RAW-Bibliothek)."""
    with open(fs(path), "rb") as fh:
        data = fh.read(min(size, RAW_SCAN))
    best, best_px = None, 0
    starts = [m.start() for m in re.finditer(b"\xff\xd8\xff[\xdb\xe0\xe1\xc0\xc4\xee]", data)][:40]
    for st in starts:
        try:
            im = Image.open(io.BytesIO(data[st:]))
            w, h = im.size
            if w * h > best_px and w >= 160:
                im.draft("RGB", (box[0] * 2, box[1] * 2))
                im.load()
                best, best_px = im, w * h
        except Exception:
            continue
    if best is not None:
        try:
            best = ImageOps.exif_transpose(best)
        except Exception:
            pass
    return best


def _pdf(path, size, box):
    import pypdfium2 as pdfium  # optional
    doc = pdfium.PdfDocument(fs(path))
    try:
        page = doc[0]
        w, h = page.get_size()
        scale = min(box[0] * 2 / max(w, 1), box[1] * 2 / max(h, 1), 3.0)
        img = page.render(scale=scale).to_pil()
        page.close()
        return img
    finally:
        doc.close()


def _zip_thumb(path, size, box):
    with zipfile.ZipFile(fs(path)) as z:
        names = z.namelist()
        for pat in ZIP_THUMBS:
            for n in names:
                if re.fullmatch(pat, n, flags=re.IGNORECASE):
                    info = z.getinfo(n)
                    if info.file_size > 20 * 1024 * 1024:
                        continue
                    im = Image.open(io.BytesIO(z.read(n)))
                    im.load()
                    return im
    return None


_GCODE_THUMB = re.compile(rb"; thumbnail(?:_(PNG|JPG|QOI))? begin (\d+)x(\d+) \d+\r?\n(.*?); thumbnail(?:_\w+)? end",
                          re.S)


def _gcode_thumb(path, size, box):
    with open(fs(path), "rb") as fh:
        head = fh.read(4 * 1024 * 1024)
    best, best_px = None, 0
    for m in _GCODE_THUMB.finditer(head):
        kind, w, h, body = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        if kind == b"QOI":
            continue
        b64 = b"".join(line.lstrip(b"; ").strip() for line in body.splitlines())
        try:
            im = Image.open(io.BytesIO(base64.b64decode(b64)))
            im.load()
        except Exception:
            continue
        if w * h > best_px:
            best, best_px = im, w * h
    if best is not None and best.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", best.size, (60, 60, 60))
        bg.paste(best.convert("RGBA"), mask=best.convert("RGBA").split()[-1])
        best = bg
    return best


# --------------------------------------------------------------- 3D-Darstellung
def _read_stl(path, size, limit=60000):
    tris = []
    with open(fs(path), "rb") as fh:
        head = fh.read(84)
        if len(head) < 84:
            return tris
        n = struct.unpack("<I", head[80:84])[0]
        if 84 + n * 50 == size and n > 0:  # binaer
            step = max(1, n // limit)
            for i in range(0, n, step):
                fh.seek(84 + i * 50 + 12)
                v = struct.unpack("<9f", fh.read(36))
                tris.append(((v[0], v[1], v[2]), (v[3], v[4], v[5]), (v[6], v[7], v[8])))
            return tris
    if size > 150 * 1024 * 1024:
        return tris
    with open(fs(path), "r", encoding="ascii", errors="ignore") as fh:
        cur = []
        for line in fh:
            line = line.strip()
            if line.startswith("vertex"):
                p = line.split()
                cur.append((float(p[1]), float(p[2]), float(p[3])))
                if len(cur) == 3:
                    tris.append(tuple(cur))
                    cur = []
                    if len(tris) >= limit * 3:
                        break
    if len(tris) > limit:
        tris = tris[::len(tris) // limit + 1]
    return tris


def _read_obj(path, size, limit=60000):
    if size > 150 * 1024 * 1024:
        return []
    verts, tris = [], []
    with open(fs(path), "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("v "):
                p = line.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("f "):
                idx = []
                for tok in line.split()[1:]:
                    i = int(tok.split("/")[0])
                    idx.append(i - 1 if i > 0 else len(verts) + i)
                for k in range(1, len(idx) - 1):
                    tris.append((idx[0], idx[k], idx[k + 1]))
    if len(tris) > limit:
        tris = tris[::len(tris) // limit + 1]
    out = []
    for a, b, c in tris:
        try:
            out.append((verts[a], verts[b], verts[c]))
        except IndexError:
            continue
    return out


def render_mesh(tris, box=(360, 260)):
    """Isometrische, flach schattierte Darstellung (Maler-Algorithmus)."""
    if not tris:
        return None
    import math
    W, H = box[0] * 2, box[1] * 2
    ax, az = math.radians(-60), math.radians(35)  # Kamera: schraeg von oben
    ca, sa, cz, sz = math.cos(ax), math.sin(ax), math.cos(az), math.sin(az)

    def rot(p):
        x, y, z = p
        x, y = x * cz - y * sz, x * sz + y * cz          # um Z
        y, z = y * ca - z * sa, y * sa + z * ca          # um X
        return x, y, z
    rt = [tuple(rot(p) for p in t) for t in tris]
    xs = [p[0] for t in rt for p in t]
    ys = [p[1] for t in rt for p in t]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny) or 1.0
    sc = 0.86 * min(W, H) / span
    ox = (W - (maxx - minx) * sc) / 2 - minx * sc
    oy = (H - (maxy - miny) * sc) / 2 - miny * sc
    light = (0.35, -0.45, 0.82)
    ll = math.sqrt(sum(v * v for v in light))
    light = tuple(v / ll for v in light)
    faces = []
    for a, b, c in rt:
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        shade = abs(nx * light[0] + ny * light[1] + nz * light[2]) / nl
        depth = (a[2] + b[2] + c[2]) / 3
        faces.append((depth, shade, a, b, c))
    faces.sort(key=lambda f: f[0])
    img = Image.new("RGB", (W, H), (58, 58, 58))
    dr = ImageDraw.Draw(img)
    for _, shade, a, b, c in faces:
        k = 0.35 + 0.65 * shade
        col = (int(242 * k), int(140 * k), int(40 * k))
        dr.polygon([(a[0] * sc + ox, H - (a[1] * sc + oy)), (b[0] * sc + ox, H - (b[1] * sc + oy)),
                    (c[0] * sc + ox, H - (c[1] * sc + oy))], fill=col)
    return img


def _stl(path, size, box):
    return render_mesh(_read_stl(path, size), box)


def _obj(path, size, box):
    return render_mesh(_read_obj(path, size), box)


# --------------------------------------------------------------- Video / System
def _video(path, size, box):
    exe = shutil.which("ffmpeg")
    if not exe:
        return None
    flags = 0x08000000 if IS_WIN else 0
    for ss in ("1", "0"):
        r = subprocess.run([exe, "-v", "error", "-ss", ss, "-i", fs(path), "-frames:v", "1",
                            "-vf", f"scale={box[0] * 2}:-1", "-f", "image2pipe", "-vcodec", "png", "-"],
                           capture_output=True, timeout=20, creationflags=flags)
        if r.returncode == 0 and r.stdout:
            im = Image.open(io.BytesIO(r.stdout))
            im.load()
            return im
    return None


def _system_thumb(path, size, box):
    if IS_WIN:
        return _win_shell_thumb(path, max(box))
    if IS_MAC:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["qlmanage", "-t", "-s", str(max(box) * 2), "-o", tmp, path],
                           capture_output=True, timeout=20)
            for f in os.listdir(tmp):
                if f.lower().endswith(".png"):
                    im = Image.open(os.path.join(tmp, f))
                    im.load()
                    return im
    return None


def _win_shell_thumb(path, px):  # pragma: no cover - nur Windows
    """Miniatur wie im Explorer (IShellItemImageFactory) – deckt Office, PSD,
    Videos usw. ab, sofern Windows dafuer einen Vorschau-Handler kennt."""
    import ctypes
    from ctypes import POINTER, byref, c_void_p, wintypes
    ole32, shell32, gdi32, user32 = (ctypes.windll.ole32, ctypes.windll.shell32,
                                     ctypes.windll.gdi32, ctypes.windll.user32)
    ole32.CoInitializeEx(None, 0x2)

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                    ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    class SIZE(ctypes.Structure):
        _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]

    class BITMAP(ctypes.Structure):
        _fields_ = [("bmType", ctypes.c_long), ("bmWidth", ctypes.c_long), ("bmHeight", ctypes.c_long),
                    ("bmWidthBytes", ctypes.c_long), ("bmPlanes", wintypes.WORD),
                    ("bmBitsPixel", wintypes.WORD), ("bmBits", c_void_p)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    iid = GUID()
    ole32.CLSIDFromString(ctypes.c_wchar_p("{bcc18b79-ba16-442f-80c4-8a59c30c463b}"), byref(iid))
    shell32.SHCreateItemFromParsingName.argtypes = [ctypes.c_wchar_p, c_void_p, POINTER(GUID),
                                                    POINTER(c_void_p)]
    fac = c_void_p()
    if shell32.SHCreateItemFromParsingName(os.path.abspath(path), None, byref(iid), byref(fac)) != 0 \
            or not fac:
        return None
    vtbl = ctypes.cast(fac, POINTER(POINTER(c_void_p))).contents
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(vtbl[2])
    get_image = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, SIZE, ctypes.c_int,
                                   POINTER(wintypes.HBITMAP))(vtbl[3])
    hbmp = wintypes.HBITMAP()
    try:
        hr = get_image(fac, SIZE(px, px), 0x0, byref(hbmp))
    finally:
        release(fac)
    if hr != 0 or not hbmp:
        return None
    try:
        bm = BITMAP()
        gdi32.GetObjectW(hbmp, ctypes.sizeof(bm), byref(bm))
        w, h = bm.bmWidth, bm.bmHeight
        if w <= 0 or h <= 0 or w * h > 16_000_000:
            return None
        bi = BITMAPINFOHEADER()
        bi.biSize, bi.biWidth, bi.biHeight = ctypes.sizeof(bi), w, -h
        bi.biPlanes, bi.biBitCount, bi.biCompression = 1, 32, 0
        buf = ctypes.create_string_buffer(w * h * 4)
        hdc = user32.GetDC(None)
        try:
            gdi32.GetDIBits(hdc, hbmp, 0, h, buf, byref(bi), 0)
        finally:
            user32.ReleaseDC(None, hdc)
        return Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).convert("RGB")
    finally:
        gdi32.DeleteObject(hbmp)
