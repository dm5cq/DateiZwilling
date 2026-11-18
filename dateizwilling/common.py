"""Gemeinsame Bausteine: Steuerung (Pause/Abbruch), Pruefsummen, Formatierung."""
from __future__ import annotations

import hashlib
import os
import threading
import time
from typing import Callable

from .pathutil import fs

CHUNK = 1024 * 1024          # 1 MiB Lesebloecke
PARTIAL = 64 * 1024          # Anfang + Ende fuer den Schnellvergleich
SMALL_FILE = 2 * PARTIAL     # bis zu dieser Groesse wird sofort voll gehasht


class Cancelled(Exception):
    """Vom Benutzer abgebrochen."""


class Control:
    """Pause/Fortsetzen/Abbrechen fuer Hintergrundarbeiten (threadsicher)."""

    def __init__(self) -> None:
        self._run = threading.Event()
        self._run.set()
        self._cancel = threading.Event()

    def pause(self) -> None:
        self._run.clear()

    def resume(self) -> None:
        self._run.set()

    def cancel(self) -> None:
        self._cancel.set()
        self._run.set()

    @property
    def paused(self) -> bool:
        return not self._run.is_set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def checkpoint(self) -> None:
        while not self._run.wait(0.25):
            if self._cancel.is_set():
                break
        if self._cancel.is_set():
            raise Cancelled()


ProgressFn = Callable[[dict], None]


def _blake(digest: int = 32):
    return hashlib.blake2b(digest_size=digest)


def hash_partial(path: str, size: int, control: Control | None = None) -> tuple[str, bool]:
    """Schnell-Pruefsumme aus Anfang + Ende. Bei kleinen Dateien wird gleich
    die volle Pruefsumme berechnet; Rueckgabe (hash, ist_voll)."""
    if size <= SMALL_FILE:
        return hash_full(path, control), True
    h = _blake(20)
    h.update(size.to_bytes(8, "little"))
    with open(fs(path), "rb") as fh:
        h.update(fh.read(PARTIAL))
        fh.seek(max(0, size - PARTIAL))
        h.update(fh.read(PARTIAL))
    return "p" + h.hexdigest(), False


def hash_full(path: str, control: Control | None = None,
              on_bytes: Callable[[int], None] | None = None) -> str:
    h = _blake(32)
    n = 0
    with open(fs(path), "rb") as fh:
        while True:
            buf = fh.read(CHUNK)
            if not buf:
                break
            h.update(buf)
            n += 1
            if on_bytes:
                on_bytes(len(buf))
            if control is not None and n % 8 == 0:
                control.checkpoint()
    return h.hexdigest()


def files_equal(a: str, b: str, control: Control | None = None,
                on_bytes: Callable[[int], None] | None = None) -> bool:
    """Byte-fuer-Byte-Vergleich (die strengste Pruefung)."""
    try:
        if os.path.getsize(fs(a)) != os.path.getsize(fs(b)):
            return False
    except OSError:
        return False
    n = 0
    with open(fs(a), "rb") as fa, open(fs(b), "rb") as fb:
        while True:
            ba = fa.read(CHUNK)
            bb = fb.read(CHUNK)
            if ba != bb:
                return False
            if not ba:
                return True
            n += 1
            if on_bytes:
                on_bytes(len(ba))
            if control is not None and n % 8 == 0:
                control.checkpoint()


def human_size(n: float, lang: str = "de") -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    n = float(n)
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    s = f"{n:.0f}" if i == 0 else f"{n:.1f}"
    if lang == "de":
        s = s.replace(".", ",")
    return f"{s} {units[i]}"


def human_time(ns_or_s: float, lang: str = "de") -> str:
    t = ns_or_s / 1e9 if ns_or_s > 1e12 else ns_or_s
    try:
        fmt = "%d.%m.%Y %H:%M:%S" if lang == "de" else "%Y-%m-%d %H:%M:%S"
        return time.strftime(fmt, time.localtime(t))
    except (OverflowError, OSError, ValueError):
        return "?"


def human_duration(sec: float) -> str:
    sec = int(max(0, sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class RateMeter:
    """Gleitende Geschwindigkeits- und Restzeitschaetzung."""

    def __init__(self) -> None:
        self.start = time.monotonic()
        self.samples: list[tuple[float, float]] = []

    def update(self, value: float) -> None:
        now = time.monotonic()
        self.samples.append((now, value))
        cutoff = now - 10
        while len(self.samples) > 2 and self.samples[0][0] < cutoff:
            self.samples.pop(0)

    def rate(self) -> float:
        if len(self.samples) < 2:
            return 0.0
        (t0, v0), (t1, v1) = self.samples[0], self.samples[-1]
        return (v1 - v0) / (t1 - t0) if t1 > t0 else 0.0

    def eta(self, remaining: float) -> float | None:
        r = self.rate()
        return remaining / r if r > 0 else None


def csv_safe(value) -> str:
    """Schutz vor CSV-/Formel-Injektion in Excel (Dateinamen wie '=HYPERLINK(...)')."""
    s = "" if value is None else str(value)
    if s[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s
