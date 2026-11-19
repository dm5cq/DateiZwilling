"""Plattform- und Pfadhilfen (Windows lange Pfade, Archivabbild, Cloud-
Platzhalter, Papierkorb, Datenordner, Einzelinstanz-Sperre)."""
from __future__ import annotations

import os
import subprocess
import sys

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"

# Windows-Dateiattribute
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
CLOUD_ONLY_MASK = (FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN
                   | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS)


# ------------------------------------------------------------- lange Pfade
def fs(path: str) -> str:
    """Wandelt einen Pfad fuer Dateisystemaufrufe um. Unter Windows wird das
    Praefix \\\\?\\ verwendet, damit auch Pfade > 260 Zeichen funktionieren."""
    if not IS_WIN or not path:
        return path
    if path.startswith("\\\\?\\"):
        return path
    p = os.path.abspath(path)
    if len(p) < 240:
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p


def unfs(path: str) -> str:
    """Entfernt das \\\\?\\-Praefix wieder (fuer Anzeige und Datenbank)."""
    if IS_WIN and path.startswith("\\\\?\\"):
        if path.startswith("\\\\?\\UNC\\"):
            return "\\\\" + path[8:]
        return path[4:]
    return path


def norm_key(path: str) -> str:
    """Eindeutiger Vergleichsschluessel fuer einen Pfad."""
    return os.path.normcase(os.path.abspath(unfs(path)))


def is_within(child: str, parent: str) -> bool:
    c, p = norm_key(child), norm_key(parent)
    if c == p:
        return True
    return c.startswith(p.rstrip("\\/") + os.sep)


# ------------------------------------------------------------- Archivabbild
def archive_target(archive_root: str, src: str) -> str:
    """Bildet den Originalpfad exakt unter dem Archiv ab.

    Windows:  D:\\Fotos\\2020\\a.jpg     -> <Archiv>\\D\\Fotos\\2020\\a.jpg
              \\\\NAS\\daten\\x\\b.docx   -> <Archiv>\\UNC\\NAS\\daten\\x\\b.docx
    macOS:    /Volumes/HDD/x/c.pdf      -> <Archiv>/Volumes/HDD/x/c.pdf
    """
    p = os.path.abspath(unfs(src))
    if IS_WIN:
        drive, rest = os.path.splitdrive(p)
        if drive.startswith("\\\\"):
            parts = [x for x in drive.split("\\") if x]
            prefix = os.path.join("UNC", *parts)
        else:
            prefix = drive.rstrip(":") or "_"
        rel = rest.lstrip("\\/")
        return os.path.join(archive_root, prefix, rel)
    return os.path.join(archive_root, p.lstrip("/"))


def unique_path(path: str) -> str:
    """Liefert *path* oder – falls belegt – 'name (DZ2).ext', 'name (DZ3).ext' …"""
    if not os.path.lexists(fs(path)):
        return path
    folder, name = os.path.split(path)
    stem, dot, ext = name.rpartition(".")
    if not dot or not stem:
        stem, ext, dot = name, "", ""
    i = 2
    while True:
        cand = os.path.join(folder, f"{stem} (DZ{i}){dot}{ext}")
        if not os.path.lexists(fs(cand)):
            return cand
        i += 1


# ------------------------------------------------------------- Attribute
def is_cloud_only(st: os.stat_result) -> bool:
    """True fuer OneDrive/pCloud/iCloud-Platzhalter, deren Inhalt erst
    heruntergeladen werden muesste."""
    attrs = getattr(st, "st_file_attributes", 0)
    if attrs & CLOUD_ONLY_MASK:
        return True
    if IS_MAC:
        flags = getattr(st, "st_flags", 0)
        if flags & 0x40000000:  # SF_DATALESS (iCloud "nur in der Cloud")
            return True
    return False


def is_hidden(name: str, st: os.stat_result | None) -> bool:
    if name.startswith("."):
        return True
    attrs = getattr(st, "st_file_attributes", 0) if st is not None else 0
    return bool(attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM))


def is_network_path(path: str) -> bool:
    """Netzlaufwerke haben keinen Papierkorb – Loeschen waere dort endgueltig."""
    p = os.path.abspath(unfs(path))
    if IS_WIN:
        if p.startswith("\\\\"):
            return True
        try:
            import ctypes
            root = os.path.splitdrive(p)[0] + "\\"
            return ctypes.windll.kernel32.GetDriveTypeW(root) == 4  # DRIVE_REMOTE
        except Exception:
            return False
    if IS_MAC:
        try:
            out = subprocess.run(["df", "-P", p], capture_output=True, text=True, timeout=10).stdout
            dev = out.splitlines()[-1].split()[0] if out else ""
            return dev.startswith("//") or ":" in dev.split("/")[0]
        except (OSError, subprocess.SubprocessError, IndexError):
            return False
    return False


# ------------------------------------------------------------- Datenordner
def app_base_dir() -> str:
    if getattr(sys, "frozen", False):
        exe = sys.executable
        # macOS .app: …/DateiZwilling.app/Contents/MacOS/DateiZwilling
        if IS_MAC and ".app/Contents/MacOS" in exe:
            return os.path.abspath(os.path.join(os.path.dirname(exe), "..", "..", ".."))
        return os.path.dirname(os.path.abspath(exe))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _writable(folder: str) -> bool:
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, ".dz_write_test")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def data_dir() -> str:
    """Portabel: 'DateiZwilling-Daten' neben der EXE. Ist dort kein
    Schreibzugriff, wird der Benutzer-Datenordner verwendet."""
    override = os.environ.get("DATEIZWILLING_DATA")
    if override and _writable(override):
        return override
    portable = os.path.join(app_base_dir(), "DateiZwilling-Daten")
    if _writable(portable):
        return portable
    if IS_WIN:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif IS_MAC:
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    folder = os.path.join(base, "DateiZwilling")
    os.makedirs(folder, exist_ok=True)
    return folder


def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", None) or app_base_dir()
    return os.path.join(base, rel)


# ------------------------------------------------------------- Einzelinstanz
class InstanceLock:
    """Verhindert, dass zwei Instanzen gleichzeitig dieselbe Datenbank und
    dasselbe Archiv bearbeiten."""

    def __init__(self, folder: str):
        self.path = os.path.join(folder, "dateizwilling.lock")
        self._fh = None

    def acquire(self) -> bool:
        try:
            self._fh = open(self.path, "a+")
            if IS_WIN:
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            if self._fh:
                self._fh.close()
                self._fh = None
            return False

    def release(self) -> None:
        if not self._fh:
            return
        try:
            if IS_WIN:
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        self._fh.close()
        self._fh = None


# ------------------------------------------------------------- Papierkorb
def send_to_trash(paths: list[str]) -> tuple[list[str], list[str]]:
    """Verschiebt Dateien in den Papierkorb. Rueckgabe (ok, fehlgeschlagen).
    Fehlgeschlagene Dateien werden NICHT endgueltig geloescht."""
    ok: list[str] = []
    failed: list[str] = []
    if not paths:
        return ok, failed
    if IS_WIN:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR),
            ]
        FO_DELETE = 3
        flags = 0x0040 | 0x0010 | 0x0004 | 0x0400  # ALLOWUNDO|NOCONFIRMATION|SILENT|NOERRORUI
        for p in paths:
            op = SHFILEOPSTRUCTW()
            op.wFunc = FO_DELETE
            op.pFrom = os.path.abspath(unfs(p)) + "\0\0"
            op.fFlags = flags
            res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
            if res == 0 and not op.fAnyOperationsAborted and not os.path.exists(fs(p)):
                ok.append(p)
            else:
                failed.append(p)
        return ok, failed
    if IS_MAC:
        for p in paths:
            script = ('tell application "Finder" to delete POSIX file "%s"'
                      % os.path.abspath(p).replace("\\", "\\\\").replace('"', '\\"'))
            try:
                subprocess.run(["osascript", "-e", script], check=True,
                               capture_output=True, timeout=60)
                ok.append(p) if not os.path.exists(p) else failed.append(p)
            except (OSError, subprocess.SubprocessError):
                failed.append(p)
        return ok, failed
    # Linux: freedesktop-Papierkorb (vereinfachter Fallback)
    trash = os.path.expanduser("~/.local/share/Trash/files")
    try:
        os.makedirs(trash, exist_ok=True)
    except OSError:
        return ok, list(paths)
    for p in paths:
        try:
            os.rename(p, unique_path(os.path.join(trash, os.path.basename(p))))
            ok.append(p)
        except OSError:
            failed.append(p)
    return ok, failed


def reveal_in_file_manager(path: str) -> None:
    path = os.path.abspath(path)
    try:
        if IS_WIN:
            subprocess.Popen(["explorer", "/select,", path])
        elif IS_MAC:
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])
    except OSError:
        pass


def open_with_default_app(path: str) -> None:
    try:
        if IS_WIN:
            os.startfile(path)  # type: ignore[attr-defined]
        elif IS_MAC:
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        pass


# =====================================================================
# 2.0 – Laufwerke, Dateisysteme, Warnungen, Wachhalten
# =====================================================================
import errno as _errno  # noqa: E402
import re as _re  # noqa: E402
import shutil as _shutil  # noqa: E402

# Netzwerk-/Geraetefehler, nach denen sich ein Wiederholen lohnt
TRANSIENT_WINERRORS = {21, 53, 59, 64, 67, 121, 1167, 1231, 1232, 1236, 1311}
TRANSIENT_ERRNOS = {getattr(_errno, n) for n in ("EIO", "ENOTCONN", "EHOSTDOWN", "EHOSTUNREACH",
                                                    "ETIMEDOUT", "ESTALE", "ENETDOWN", "ENETUNREACH",
                                                    "ECONNRESET", "ENXIO", "ENODEV")
                    if hasattr(_errno, n)}


def is_transient_error(exc: BaseException) -> bool:
    if not isinstance(exc, OSError):
        return False
    if getattr(exc, "winerror", None) in TRANSIENT_WINERRORS:
        return True
    return exc.errno in TRANSIENT_ERRNOS


def volume_root(path: str) -> str:
    """Wurzel des Laufwerks/der Freigabe: 'D:\\', '\\\\NAS\\daten\\', '/Volumes/X', '/'."""
    p = os.path.abspath(unfs(path))
    if IS_WIN:
        drive = os.path.splitdrive(p)[0]
        return drive + "\\" if drive else p[:3]
    if p.startswith("/Volumes/"):
        parts = p.split("/")
        return "/".join(parts[:3])
    if p.startswith(("/media/", "/mnt/", "/run/media/")):
        parts = p.split("/")
        n = 4 if p.startswith("/run/media/") else 3
        return "/".join(parts[:n + (1 if p.startswith("/media/") and len(parts) > 3 else 0)])
    return "/"


def is_reachable(path: str) -> bool:
    try:
        return os.path.isdir(fs(volume_root(path)))
    except OSError:
        return False


def disk_free(path: str) -> int | None:
    """Freier Speicher auf dem Laufwerk von *path* (naechster existierender Ordner)."""
    p = os.path.abspath(unfs(path))
    while p and not os.path.exists(fs(p)):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    try:
        return _shutil.disk_usage(fs(p)).free
    except OSError:
        return None


def same_device(a: str, b: str) -> bool:
    def dev(x: str):
        p = os.path.abspath(unfs(x))
        while not os.path.exists(fs(p)):
            parent = os.path.dirname(p)
            if parent == p:
                return None
            p = parent
        try:
            return os.stat(fs(p)).st_dev
        except OSError:
            return None
    da, db = dev(a), dev(b)
    return da is not None and da == db


def fs_type(path: str) -> str:
    """Dateisystemname in Kleinbuchstaben ('ntfs', 'fat32', 'exfat', 'apfs', 'msdos' …)."""
    p = os.path.abspath(unfs(path))
    if IS_WIN:
        try:
            import ctypes
            root = volume_root(p)
            buf = ctypes.create_unicode_buffer(64)
            label = ctypes.create_unicode_buffer(261)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(root), label, 261, None, None, None, buf, 64)
            return buf.value.lower() if ok else ""
        except Exception:
            return ""
    try:
        if IS_MAC:
            out = subprocess.run(["df", "-P", p], capture_output=True, text=True, timeout=10).stdout
            mnt = out.splitlines()[-1].split()[-1] if out else "/"
            mounts = subprocess.run(["mount"], capture_output=True, text=True, timeout=10).stdout
            for line in mounts.splitlines():
                if f" on {mnt} (" in line:
                    return line.split("(", 1)[1].split(",", 1)[0].strip().lower()
            return ""
        best, typ = "", ""
        with open("/proc/mounts", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) > 2 and (p == parts[1] or p.startswith(parts[1].rstrip("/") + "/")) \
                        and len(parts[1]) >= len(best):
                    best, typ = parts[1], parts[2].lower()
        return typ
    except (OSError, subprocess.SubprocessError, IndexError):
        return ""


def volume_label(path: str) -> str:
    if not IS_WIN:
        return os.path.basename(volume_root(path))
    try:
        import ctypes
        label = ctypes.create_unicode_buffer(261)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(volume_root(path)), label, 261, None, None, None, None, 0)
        return label.value if ok else ""
    except Exception:
        return ""


FAT_TYPES = {"fat", "fat12", "fat16", "fat32", "vfat", "msdos"}
WINLIKE_TYPES = FAT_TYPES | {"exfat", "ntfs", "ntfs3", "fuseblk", "refs"}
FAT32_MAX = 4 * 1024 ** 3 - 1
_BAD_CHARS = _re.compile(r'[<>:"|?*\x00-\x1f]')
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def needs_safe_names(archive: str) -> bool:
    return IS_WIN or fs_type(archive) in WINLIKE_TYPES


def safe_component(name: str) -> str:
    """Macht einen Dateinamen fuer FAT/exFAT/NTFS gueltig (Zeichen, Punkte am Ende, reservierte Namen)."""
    new = _BAD_CHARS.sub("_", name).rstrip(" .") or "_"
    if new.split(".", 1)[0].lower() in _RESERVED:
        new = "_" + new
    return new


def safe_relpath(path: str) -> str:
    parts = _re.split(r"[\\/]", path)
    out = []
    for i, part in enumerate(parts):
        if i == 0 and (part.endswith(":") or part == ""):
            out.append(part)
        else:
            out.append(safe_component(part) if part else part)
    return os.sep.join(out)


# ------------------------------------------------------------- Warnungen
def cloud_sync_kind(path: str) -> str | None:
    """Erkennt Ordner, die ein Cloud-Dienst synchronisiert."""
    p = os.path.abspath(unfs(path)).replace("\\", "/").lower()
    for env in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        v = os.environ.get(env)
        if v and (p + "/").startswith(v.replace("\\", "/").lower().rstrip("/") + "/"):
            return "OneDrive"
    markers = [("/onedrive", "OneDrive"), ("pcloud drive", "pCloud"), ("pclouddrive", "pCloud"),
               ("/pcloud", "pCloud"), ("/nextcloud", "Nextcloud"), ("/owncloud", "ownCloud"),
               ("/dropbox", "Dropbox"), ("/google drive", "Google Drive"), ("/googledrive", "Google Drive"),
               ("/icloud drive", "iCloud"), ("/icloudrive", "iCloud"), ("/library/mobile documents", "iCloud"),
               ("/library/cloudstorage", "Cloud"), ("/synologydrive", "Synology Drive"), ("/box/", "Box"),
               ("/megasync", "MEGA"), ("/mega/", "MEGA")]
    for m, name in markers:
        if m in p:
            return name
    label = volume_label(path).lower()
    if "pcloud" in label:
        return "pCloud"
    return None


def risky_source(path: str) -> str | None:
    """Warnt vor Laufwerkswurzeln und System-/Programmordnern als Quelle."""
    p = os.path.abspath(unfs(path))
    norm = os.path.normcase(p).rstrip("\\/")
    if norm == os.path.normcase(volume_root(p)).rstrip("\\/") or norm in ("", "/"):
        return "root"
    home = os.path.normcase(os.path.expanduser("~")).rstrip("\\/")
    if norm == home:
        return "home"
    sysdirs = []
    if IS_WIN:
        for env in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData", "APPDATA", "LOCALAPPDATA"):
            v = os.environ.get(env)
            if v:
                sysdirs.append(v)
    else:
        sysdirs += ["/System", "/Library", "/Applications", "/usr", "/bin", "/etc", "/private",
                    os.path.expanduser("~/Library")]
    for d in sysdirs:
        dn = os.path.normcase(os.path.abspath(d)).rstrip("\\/")
        if norm == dn or norm.startswith(dn + os.sep):
            return "system"
    return None


# ------------------------------------------------------------- Anonymisieren
def anonymize_path(path: str) -> str:
    home = os.path.expanduser("~")
    user = os.path.basename(home.rstrip("\\/"))
    out = path
    if home and out.lower().startswith(home.lower()):
        out = "~" + out[len(home):]
    if user and len(user) > 2:
        out = _re.sub(_re.escape(user), "<Benutzer>", out, flags=_re.IGNORECASE)
    return out


# ------------------------------------------------------------- Zeitstempel/Attribute (Windows)
def copy_windows_metadata(src: str, dst: str) -> None:
    """Uebernimmt Erstellungsdatum und Attribute (schreibgeschuetzt/versteckt/Archiv)."""
    if not IS_WIN:
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        st = os.stat(fs(src))
        ns = getattr(st, "st_birthtime_ns", None) or int(st.st_ctime * 1e9)
        ft = int(ns // 100) + 116444736000000000
        ctime = wintypes.FILETIME(ft & 0xFFFFFFFF, ft >> 32)
        CreateFileW = k32.CreateFileW
        CreateFileW.restype = wintypes.HANDLE
        h = CreateFileW(ctypes.c_wchar_p(fs(dst)), 0x100, 0x7, None, 3, 0x02000000, None)
        if h and h != wintypes.HANDLE(-1).value:
            k32.SetFileTime(h, ctypes.byref(ctime), None, None)
            k32.CloseHandle(h)
        attrs = getattr(st, "st_file_attributes", 0) & (0x1 | 0x2 | 0x4 | 0x20)
        if attrs:
            k32.SetFileAttributesW(ctypes.c_wchar_p(fs(dst)), attrs)
    except Exception:
        pass


# ------------------------------------------------------------- Ruhezustand verhindern
class KeepAwake:
    """Verhindert Standby, solange ein Scan/Archivierungslauf aktiv ist."""

    def __init__(self) -> None:
        self._proc = None

    def __enter__(self) -> "KeepAwake":
        try:
            if IS_WIN:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            elif IS_MAC:
                self._proc = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return self

    def __exit__(self, *exc) -> None:
        try:
            if IS_WIN:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            elif self._proc is not None:
                self._proc.terminate()
        except Exception:
            pass


# ------------------------------------------------------------- SSD/HDD
_MEDIA_CACHE: dict[str, str] = {}


def media_kind(path: str) -> str:
    """'ssd', 'hdd', 'network' oder 'unknown'."""
    if is_network_path(path):
        return "network"
    root = volume_root(path)
    if root in _MEDIA_CACHE:
        return _MEDIA_CACHE[root]
    kind = "unknown"
    try:
        if IS_WIN and len(root) >= 2 and root[1] == ":":
            cmd = ("(Get-PhysicalDisk -DeviceNumber (Get-Partition -DriveLetter %s).DiskNumber)"
                   ".MediaType" % root[0])
            out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True,
                                 text=True, timeout=12, creationflags=0x08000000).stdout.strip().lower()
            kind = "ssd" if "ssd" in out else ("hdd" if "hdd" in out else "unknown")
        elif IS_MAC:
            out = subprocess.run(["diskutil", "info", root], capture_output=True, text=True,
                                 timeout=12).stdout.lower()
            if "solid state:" in out:
                kind = "ssd" if "solid state:               yes" in out or "solid state: yes" in \
                    " ".join(out.split()) else "hdd"
        else:
            dev = ""
            with open("/proc/mounts", encoding="utf-8") as fh:
                for line in fh:
                    parts = line.split()
                    if parts[1] == root:
                        dev = os.path.basename(parts[0])
            base = _re.sub(r"\d+$", "", dev)
            rot = f"/sys/block/{base}/queue/rotational"
            if base and os.path.exists(rot):
                with open(rot, encoding="ascii") as fh:
                    kind = "hdd" if fh.read().strip() == "1" else "ssd"
    except (OSError, subprocess.SubprocessError, IndexError, ValueError):
        pass
    _MEDIA_CACHE[root] = kind
    return kind


def auto_workers(paths: list[str]) -> int:
    kinds = {media_kind(p) for p in paths} or {"unknown"}
    if "hdd" in kinds:
        return 1
    if "network" in kinds or "unknown" in kinds:
        return 2
    return 4
