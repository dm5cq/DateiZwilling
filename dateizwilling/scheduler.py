"""Zeitgesteuerter Scan (F7) ueber die Windows-Aufgabenplanung bzw. macOS launchd.

Der geplante Lauf erstellt NUR einen Bericht (HTML) im Archivordner unter
_DateiZwilling/Berichte – es wird dabei nie etwas verschoben oder geloescht.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys

from .pathutil import IS_MAC, IS_WIN, app_base_dir

TASK_NAME = "DateiZwilling Bericht"
LAUNCHD_LABEL = "de.kaiser-burghausen.dateizwilling.bericht"
WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _base_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, os.path.join(app_base_dir(), "DateiZwilling.py")]


def scan_command(sources: list[str], archive: str, extra: list[str] | None = None) -> list[str]:
    cmd = _base_command() + ["--cli", "scan"]
    for s in sources:
        cmd += ["-s", s]
    cmd += ["-a", archive, "--report-dir", os.path.join(archive, "_DateiZwilling", "Berichte")]
    return cmd + (extra or [])


def _quote_cmd(arg: str) -> str:
    """Quoting fuer eine .cmd-Datei: Prozentzeichen verdoppeln (sonst als Variable gelesen),
    Argumente mit Sonderzeichen in Anfuehrungszeichen."""
    arg = arg.replace("%", "%%")
    return '"' + arg.replace('"', '""') + '"' if any(c in arg for c in ' &()^|<>"%') or not arg else arg


def create(data_dir: str, sources: list[str], archive: str, weekly: bool, weekday: int,
           hhmm: str, extra: list[str] | None = None) -> tuple[bool, str]:
    """Legt die Aufgabe an (bzw. ersetzt sie). Rueckgabe (ok, Meldung)."""
    hh, mm = (int(x) for x in hhmm.split(":"))
    if not (0 <= hh < 24 and 0 <= mm < 60):
        return False, "Ungueltige Uhrzeit"
    cmd = scan_command(sources, archive, extra)
    if IS_WIN:
        script = os.path.join(data_dir, "Zeitplan-Bericht.cmd")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("@echo off\r\nchcp 65001 >nul\r\n" + " ".join(_quote_cmd(a) for a in cmd) + "\r\n")
        args = ["schtasks", "/Create", "/F", "/TN", TASK_NAME, "/TR", f'"{script}"', "/ST", f"{hh:02d}:{mm:02d}"]
        args += ["/SC", "WEEKLY", "/D", WEEKDAYS[weekday]] if weekly else ["/SC", "DAILY"]
        r = subprocess.run(args, capture_output=True, text=True, creationflags=0x08000000)
        return r.returncode == 0, (r.stdout or r.stderr).strip()
    if IS_MAC:
        agents = os.path.expanduser("~/Library/LaunchAgents")
        os.makedirs(agents, exist_ok=True)
        plist = os.path.join(agents, LAUNCHD_LABEL + ".plist")
        cal = {"Hour": hh, "Minute": mm}
        if weekly:
            cal["Weekday"] = (weekday + 1) % 7  # launchd: 0 = Sonntag
        with open(plist, "wb") as fh:
            plistlib.dump({"Label": LAUNCHD_LABEL, "ProgramArguments": cmd,
                           "StartCalendarInterval": cal, "RunAtLoad": False}, fh)
        subprocess.run(["launchctl", "unload", plist], capture_output=True)
        r = subprocess.run(["launchctl", "load", plist], capture_output=True, text=True)
        return r.returncode == 0, (r.stdout or r.stderr or plist).strip()
    return False, "Zeitplan wird auf diesem System nicht unterstuetzt"


def remove() -> tuple[bool, str]:
    if IS_WIN:
        r = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], capture_output=True,
                           text=True, creationflags=0x08000000)
        return r.returncode == 0, (r.stdout or r.stderr).strip()
    if IS_MAC:
        plist = os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCHD_LABEL}.plist")
        subprocess.run(["launchctl", "unload", plist], capture_output=True)
        try:
            os.remove(plist)
        except OSError:
            pass
        return True, plist
    return False, ""


def exists() -> bool:
    try:
        if IS_WIN:
            r = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME], capture_output=True,
                               creationflags=0x08000000)
            return r.returncode == 0
        if IS_MAC:
            return os.path.exists(os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCHD_LABEL}.plist"))
    except OSError:
        pass
    return False
