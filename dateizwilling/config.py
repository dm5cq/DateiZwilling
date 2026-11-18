"""Einstellungen (JSON, atomar gespeichert)."""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger("dateizwilling.config")

DEFAULTS: dict = {
    "lang": "de",
    "sources": [],
    "archive": "",
    "protected": [],
    "excludes": [],
    "categories": [],
    "keep_rule": "oldest",
    "prefer_source_order": True,
    "workers": 2,
    "verify_bytes": True,
    "move_sidecars": True,
    "include_hidden": False,
    "skip_cloud_only": True,
    "protect_catalogs": True,
    "min_size": 1,
    "high_contrast": False,
    "font_scale": 1.0,
    "tts": False,
    "geometry": "",
    "maximized": False,
}


def load(folder: str) -> dict:
    path = os.path.join(folder, "einstellungen.json")
    cfg = dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            for k, v in data.items():
                if k in DEFAULTS and isinstance(v, type(DEFAULTS[k])) or (
                        k in DEFAULTS and isinstance(DEFAULTS[k], float) and isinstance(v, int)):
                    cfg[k] = v
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        log.warning("Einstellungen nicht lesbar (%s) – Standardwerte", exc)
    cfg["workers"] = max(1, min(16, int(cfg["workers"])))
    cfg["font_scale"] = max(0.8, min(2.0, float(cfg["font_scale"])))
    return cfg


def save(folder: str, cfg: dict) -> None:
    path = os.path.join(folder, "einstellungen.json")
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({k: cfg.get(k, v) for k, v in DEFAULTS.items()}, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        log.warning("Einstellungen nicht gespeichert: %s", exc)
