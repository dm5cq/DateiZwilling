"""Dateikategorien, Begleitdateien und Schutzregeln.

Wichtig: DateiZwilling vergleicht den *Inhalt* (Byte fuer Byte bzw. per
BLAKE2b-Pruefsumme). Deshalb wird JEDES Dateiformat unterstuetzt – auch
unbekannte. Die Kategorien dienen nur zum Filtern und zur Anzeige.
"""
from __future__ import annotations

import fnmatch
import os

# ---------------------------------------------------------------- Kategorien
CATEGORIES: dict[str, set[str]] = {
    "office": {
        # Word
        "doc", "docx", "docm", "dot", "dotx", "dotm", "rtf", "wbk", "wps", "wpd",
        # Excel
        "xls", "xlsx", "xlsm", "xlsb", "xlt", "xltx", "xltm", "xla", "xlam", "csv",
        # PowerPoint
        "ppt", "pptx", "pptm", "pps", "ppsx", "ppsm", "pot", "potx", "potm", "ppam",
        # Access
        "mdb", "accdb", "accde", "accdt", "accdr", "mde", "adp", "laccdb",
        # Publisher, OneNote, Visio, Project, Outlook
        "pub", "one", "onepkg", "vsd", "vsdx", "vsdm", "vss", "vssx", "vst", "vstx",
        "mpp", "mpt", "msg", "oft", "pst", "ost", "eml", "vcf", "ics", "xps", "oxps",
        # LibreOffice / OpenOffice / StarOffice
        "odt", "ott", "ods", "ots", "odp", "otp", "odg", "otg", "odb", "odf", "odm",
        "sxw", "sxc", "sxi", "sxd", "fodt", "fods", "fodp",
        # Apple iWork, WPS, Softmaker
        "pages", "numbers", "key", "et", "dps", "tmdx", "pmdx", "prdx",
    },
    "pdf": {"pdf", "fdf", "xfdf", "djvu", "epub", "mobi", "azw3"},
    "image": {
        "jpg", "jpeg", "jpe", "jfif", "png", "gif", "bmp", "dib", "tif", "tiff",
        "webp", "heic", "heif", "hif", "avif", "jxl", "jp2", "j2k", "ico", "icns",
        "tga", "pcx", "ppm", "pgm", "pbm", "pnm", "exr", "hdr", "dds", "svg", "svgz",
        "emf", "wmf", "eps", "wdp", "jxr",
        # Seestar / Astro
        "fit", "fits", "fts", "xisf", "ser",
    },
    "raw": {
        "raf",                      # Fujifilm
        "nef", "nrw",               # Nikon
        "cr2", "cr3", "crw",        # Canon
        "rw2", "raw",               # Panasonic / Leica
        "orf", "ori", "ors",        # OM System / Olympus
        "rwl", "dng",               # Leica / Adobe-DNG (DJI, Insta360, Smartphones)
        "3fr", "fff", "iiq",        # Hasselblad / Phase One
        "arw", "srf", "sr2",        # Sony
        "pef", "ptx",               # Pentax
        "x3f",                      # Sigma
        "srw",                      # Samsung
        "mrw",                      # Minolta
        "kdc", "dcr", "dcs",        # Kodak
        "erf", "mef", "mos", "mdc", "bay", "cap", "eip", "gpr",  # Epson/Mamiya/Leaf/GoPro
        "insp",                     # Insta360 Foto
    },
    "adobe": {
        "psd", "psb", "ai", "ait", "indd", "indt", "indb", "idml", "inx", "icml",
        "aep", "aet", "aepx", "prproj", "prel", "plb", "xd", "fla", "xfl", "swf",
        "sesx", "aup3", "abr", "asl", "aco", "ase", "act", "pat", "grd", "atn",
        "xmp", "lrtemplate", "lrcat", "lrdata", "lrprev", "dcp", "xmp", "pdn",
        "chproj", "rush", "pproj", "mogrt", "aex",
    },
    "affinity": {
        "af", "afphoto", "afdesign", "afpub", "aftemplate", "afpalette",
        "afbrushes", "afassets", "afstyles", "afmacro", "afmacros", "afpackage",
    },
    "captureone": {
        "cos", "cop", "cot", "costyle", "costylepack", "coplate", "comask",
        "cosessiondb", "cocatalogdb", "coaudio", "cocatalog", "cosession", "eip",
    },
    "3d": {
        # 3D-Druck: Modelle, Projekte, Slicer-Ausgaben
        "stl", "3mf", "obj", "mtl", "amf", "ply", "off", "wrl", "x3d", "gltf", "glb", "fbx",
        "dae", "3ds", "blend", "blend1", "scad", "fcstd", "fcstd1", "f3d", "f3z", "skp",
        "gcode", "gco", "g", "bgcode", "x3g", "makerbot", "ufp", "sl1", "sl1s", "ctb", "cbddlp",
        "photon", "pwmx", "pwma", "pws", "pw0", "lys", "chitubox", "lychee", "goo", "prusa",
        "curaprofile", "orca_printer", "orca_filament",
        # CAD
        "step", "stp", "iges", "igs", "sldprt", "sldasm", "slddrw", "ipt", "iam", "idw",
        "catpart", "catproduct", "prt", "asm", "x_t", "x_b", "sat", "dwg", "dxf", "dwf",
    },
    "video": {
        "mp4", "m4v", "mov", "avi", "mkv", "wmv", "mpg", "mpeg", "m2ts", "mts", "ts",
        "3gp", "webm", "flv", "vob", "insv", "lrv", "dav", "braw", "r3d", "mxf", "ogv",
    },
    "audio": {
        "mp3", "wav", "flac", "aac", "m4a", "ogg", "oga", "opus", "wma", "aiff",
        "aif", "alac", "ape", "mid", "midi", "amr",
    },
    "archive": {
        "zip", "7z", "rar", "tar", "gz", "tgz", "bz2", "xz", "zst", "iso", "img",
        "dmg", "cab", "msi", "pkg", "deb", "rpm", "apk", "exe",
    },
    "text": {
        "txt", "md", "log", "json", "xml", "yaml", "yml", "ini", "cfg", "conf",
        "html", "htm", "css", "js", "ts", "py", "c", "h", "cpp", "java", "cs",
        "sql", "sh", "bat", "ps1", "adi", "adif", "cbr", "cbz", "gpx", "kml", "kmz",
    },
}

CATEGORY_ORDER = [
    "office", "pdf", "image", "raw", "adobe", "affinity", "captureone", "3d",
    "video", "audio", "archive", "text", "other",
]

_EXT_TO_CAT: dict[str, str] = {}
for _cat in CATEGORY_ORDER:
    for _ext in CATEGORIES.get(_cat, ()):
        _EXT_TO_CAT.setdefault(_ext, _cat)

PREVIEWABLE = {
    "jpg", "jpeg", "jpe", "jfif", "png", "gif", "bmp", "dib", "tif", "tiff",
    "webp", "ico", "tga", "ppm", "pgm", "pbm", "pnm",
}


def ext_of(path: str) -> str:
    name = os.path.basename(path)
    if "." not in name.strip("."):
        return ""
    return name.rsplit(".", 1)[-1].lower()


def category_of(path: str) -> str:
    return _EXT_TO_CAT.get(ext_of(path), "other")


# ------------------------------------------------ Dateien, die nie angefasst werden
# Temporaere / Sperr- / Systemdateien: werden weder gescannt noch verschoben.
SKIP_FILE_PATTERNS = [
    "~$*",            # Office-Sperrdatei
    ".~lock.*#",      # LibreOffice-Sperrdatei
    "~wrl*.tmp", "~wrd*.tmp",
    "thumbs.db", "ehthumbs.db", "desktop.ini", "iconcache.db",
    ".ds_store", "._*", ".localized", "icon\r",
    "*.dzpart",       # eigene, unfertige Kopien
    "*.lnk",          # Verknuepfungen
    "*.dzpart.tmp",
    "pagefile.sys", "hiberfil.sys", "swapfile.sys",
]

# Ordner, in die nie hineingegangen wird
SKIP_DIR_NAMES = {
    "$recycle.bin", "system volume information", "$windows.~bt", "$windows.~ws",
    "recycler", "windows", "program files", "program files (x86)", "programdata",
    ".trash", ".trashes", ".spotlight-v100", ".fseventsd", ".documentrevisions-v100",
    ".temporaryitems", "_dateizwilling", ".git", ".svn", ".hg", "node_modules",
    "__pycache__", "@eadir", "#recycle", ".snapshot", ".zfs",
}

# Paket-/Container-Ordner: als Ganzes geschuetzt, Inhalt wird nicht angefasst,
# weil Programme (Lightroom, Fotos, Capture One, Final Cut, Logic …) sonst
# ihre Bibliothek verlieren wuerden.
PROTECTED_CONTAINER_SUFFIXES = (
    ".app", ".photoslibrary", ".photolibrary", ".aplibrary", ".migratedphotolibrary",
    ".lrdata", ".lrlibrary", ".cocatalog", ".cosessiondb.d", ".fcpbundle",
    ".logicx", ".band", ".imovielibrary", ".tvlibrary", ".musiclibrary",
    ".framework", ".bundle", ".plugin", ".kext", ".xcodeproj", ".xcworkspace",
    ".pages", ".numbers", ".key", ".rtfd", ".affinitycatalog",
)

# Einzeldateien, die als Datenbank / Katalog eines Programms dienen – werden
# standardmaessig nicht verschoben (Option), da ein "Duplikat" hier oft eine
# bewusst gesicherte Katalogkopie ist und Programme beim Fehlen abbrechen.
PROTECTED_FILE_EXTS = {
    "lrcat", "lrcat-wal", "lrcat-shm", "lrcat-data", "cocatalogdb", "cosessiondb",
    "pst", "ost", "laccdb", "ldb", "db-wal", "db-shm", "sqlite-wal", "sqlite-shm",
}


def is_skipped_file(name: str) -> bool:
    low = name.lower()
    return any(fnmatch.fnmatchcase(low, p) for p in SKIP_FILE_PATTERNS)


def is_skipped_dir(name: str) -> bool:
    return name.lower() in SKIP_DIR_NAMES


def is_protected_container(name: str) -> bool:
    return name.lower().endswith(PROTECTED_CONTAINER_SUFFIXES)


def is_protected_file(name: str) -> bool:
    return ext_of(name) in PROTECTED_FILE_EXTS


# ------------------------------------------------------------- Begleitdateien
# Begleitdateien (Sidecars) enthalten Bearbeitungen/Bewertungen zu einer Datei.
# Wird ein Duplikat archiviert, wandern seine Begleitdateien mit, damit im
# Quellordner keine verwaisten Sidecars zurueckbleiben.
SIDECAR_SUFFIX_FULL = (".xmp", ".pp3", ".dop", ".on1", ".arp", ".out.pp3")  # name.ext.xmp
SIDECAR_SUFFIX_STEM = (".xmp", ".aae", ".thm")                               # name.xmp


def find_sidecars(path: str) -> list[str]:
    """Liefert vorhandene Begleitdateien zu *path* (ohne *path* selbst)."""
    folder, name = os.path.split(path)
    stem = name.rsplit(".", 1)[0] if "." in name else name
    found: list[str] = []
    try:
        entries = {e.lower(): e for e in os.listdir(folder or ".")}
    except OSError:
        return found
    wanted = [name + s for s in SIDECAR_SUFFIX_FULL] + [stem + s for s in SIDECAR_SUFFIX_STEM]
    for w in wanted:
        real = entries.get(w.lower())
        if real and real.lower() != name.lower():
            full = os.path.join(folder, real)
            if full not in found and os.path.isfile(full):
                found.append(full)
    # Capture One: <ordner>/CaptureOne/Settings*/<name>.cos
    c1 = entries.get("captureone")
    if c1:
        c1dir = os.path.join(folder, c1)
        try:
            for sub in os.listdir(c1dir):
                if sub.lower().startswith("settings"):
                    cand = os.path.join(c1dir, sub, name + ".cos")
                    if os.path.isfile(cand):
                        found.append(cand)
        except OSError:
            pass
    return found


def sidecar_stem_shared(sidecar: str, owner: str) -> bool:
    """True, wenn *sidecar* nur ueber den Stamm (name.xmp) zugeordnet ist und
    damit evtl. auch zu einer anderen Datei gleichen Stamms gehoert (RAW+JPEG)."""
    sc = os.path.basename(sidecar).lower()
    own = os.path.basename(owner).lower()
    return not sc.startswith(own + ".")


def is_open_office_doc(path: str) -> bool:
    """True, wenn neben der Datei eine Sperrdatei von Office/LibreOffice liegt
    (Dokument ist gerade geoeffnet)."""
    folder, name = os.path.split(path)
    low = name.lower()
    try:
        entries = os.listdir(folder or ".")
    except OSError:
        return False
    for e in entries:
        el = e.lower()
        if el.startswith("~$") and len(el) > 4 and low.endswith(el[2:]):
            return True
        if el == ".~lock." + low + "#":
            return True
    return False
