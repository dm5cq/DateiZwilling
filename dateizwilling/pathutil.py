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
