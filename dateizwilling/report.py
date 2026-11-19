"""HTML- und CSV-Bericht der gefundenen Duplikate."""
from __future__ import annotations

import csv
import html
import os
import time

from . import APP_COPYRIGHT, APP_NAME, APP_VERSION
from .common import csv_safe, human_size, human_time
from .formats import CATEGORY_ORDER, category_of
from .pathutil import anonymize_path


def category_stats(groups: list[dict]) -> list[dict]:
    """Platzbedarf der Duplikate je Kategorie (F6), absteigend sortiert."""
    acc: dict[str, dict] = {}
    for g in groups:
        if g.get("kind", "same") != "same":
            continue
        cat = category_of(g["members"][0]["path"])
        a = acc.setdefault(cat, {"category": cat, "groups": 0, "duplicates": 0, "wasted": 0})
        n = sum(1 for m in g["members"] if not m.get("keep") and m.get("state", "open") == "open")
        a["groups"] += 1
        a["duplicates"] += n
        a["wasted"] += n * g["size"]
    out = [v for v in acc.values() if v["groups"]]
    out.sort(key=lambda a: (-a["wasted"], CATEGORY_ORDER.index(a["category"])
                            if a["category"] in CATEGORY_ORDER else 99))
    return out


def write_csv(path: str, groups: list[dict], anonymize: bool = False) -> None:
    fix = anonymize_path if anonymize else (lambda p: p)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Gruppe", "Rolle", "Pfad", "Groesse (Bytes)", "Geaendert", "Kategorie",
                    "BLAKE2b-256", "Status"])
        for g in groups:
            for m in g["members"]:
                w.writerow([g["gid"], "Original" if m.get("keep") else "Duplikat", csv_safe(fix(m["path"])),
                            g["size"], human_time(m["mtime_ns"]), category_of(m["path"]),
                            g["hash"], m.get("state", "open")])
    os.replace(tmp, path)


CAT_NAMES = {
    "de": {"office": "Office", "pdf": "PDF / E-Books", "image": "Bilder", "raw": "Kamera-RAW",
           "adobe": "Adobe", "affinity": "Affinity", "captureone": "Capture One", "3d": "3D-Druck & CAD",
           "video": "Video", "audio": "Audio", "archive": "Archive/Programme", "text": "Text/Code",
           "other": "Sonstige"},
    "en": {"office": "Office", "pdf": "PDF / e-books", "image": "Images", "raw": "Camera RAW",
           "adobe": "Adobe", "affinity": "Affinity", "captureone": "Capture One", "3d": "3D printing & CAD",
           "video": "Video", "audio": "Audio", "archive": "Archives/programs", "text": "Text/code",
           "other": "Other"},
}


def write_html(path: str, groups: list[dict], stats: dict | None = None, lang: str = "de",
               anonymize: bool = False) -> None:
    de = lang == "de"
    fix = anonymize_path if anonymize else (lambda p: p)
    cats = category_stats(groups)
    top = max((c["wasted"] for c in cats), default=1) or 1
    bars = "".join(
        f'<div class="bar"><span class="lbl">{html.escape(CAT_NAMES[lang if lang in CAT_NAMES else "de"].get(c["category"], c["category"]))}</span>'
        f'<span class="trk"><span class="fill" style="width:{max(1, int(100 * c["wasted"] / top))}%"></span></span>'
        f'<span class="val">{human_size(c["wasted"], lang)} · {c["duplicates"]}</span></div>' for c in cats)
    stats = stats or {}
    wasted = sum(g["size"] * sum(1 for m in g["members"] if not m.get("keep")) for g in groups
                 if g.get("kind", "same") == "same")
    rows = []
    for g in groups:
        n_dup = sum(1 for m in g["members"] if not m.get("keep"))
        rows.append(
            f'<tr class="grp"><td colspan="4">{"Gruppe" if de else "Group"} {g["gid"]} · '
            f'{len(g["members"])} {"Dateien" if de else "files"} · {human_size(g["size"], lang)} · '
            f'{"Ersparnis" if de else "Savings"} {human_size(g["size"] * n_dup, lang)}'
            f'{(" · nahezu gleich (gleicher Text)" if de else " · near-identical (same text)") if g.get("kind") == "similar" else ""}'
            f'<span class="h">{g["hash"][:16]}…</span></td></tr>')
        for m in g["members"]:
            role = ("Original" if m.get("keep") else ("Duplikat" if de else "Duplicate"))
            cls = "keep" if m.get("keep") else "dup"
            rows.append(
                f'<tr class="{cls}"><td>{role}</td><td>{html.escape(fix(m["path"]))}</td>'
                f'<td>{human_time(m["mtime_ns"], lang)}</td><td>{html.escape(m.get("state", "open"))}</td></tr>')
    doc = f"""<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">
<title>{APP_NAME} – {"Bericht" if de else "Report"}</title>
<style>
body{{background:#2b2b2b;color:#eee;font-family:Segoe UI,Helvetica,Arial,sans-serif;margin:24px}}
h1{{color:#f28c28;margin:0 0 4px}} .sub{{color:#aaa;margin-bottom:18px}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px}}
.card{{background:#363636;border-left:4px solid #f28c28;padding:10px 16px;border-radius:6px}}
.card b{{display:block;font-size:20px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
td{{padding:4px 8px;border-bottom:1px solid #3c3c3c;word-break:break-all}}
tr.grp td{{background:#3a3a3a;color:#f28c28;font-weight:600;padding-top:10px}}
tr.keep td:first-child{{color:#5cb85c;font-weight:600}} tr.dup td:first-child{{color:#f0ad4e}}
.h{{float:right;color:#888;font-family:Consolas,monospace;font-weight:400}}
footer{{margin-top:24px;color:#888;font-size:12px}}
.bars{{background:#333;border-radius:6px;padding:12px 16px;margin-bottom:18px;max-width:900px}}
.bar{{display:flex;align-items:center;gap:10px;margin:5px 0;font-size:13px}}
.lbl{{width:170px}} .trk{{flex:1;background:#3c3c3c;height:12px;border-radius:6px;overflow:hidden}}
.fill{{display:block;height:12px;background:#f28c28}} .val{{width:150px;text-align:right;color:#ccc}}
</style></head><body>
<h1>{APP_NAME} {APP_VERSION}</h1>
<div class="sub">{"Bericht vom" if de else "Report from"} {time.strftime("%d.%m.%Y %H:%M")}</div>
<div class="cards">
<div class="card">{"Gruppen" if de else "Groups"}<b>{len(groups)}</b></div>
<div class="card">{"Duplikate" if de else "Duplicates"}<b>{sum(sum(1 for m in g["members"] if not m.get("keep")) for g in groups)}</b></div>
<div class="card">{"Einsparbar" if de else "Reclaimable"}<b>{human_size(wasted, lang)}</b></div>
<div class="card">{"Gescannte Dateien" if de else "Files scanned"}<b>{stats.get("files", "–")}</b></div>
</div>
<div class="bars"><b>{"Einsparbar je Kategorie" if de else "Reclaimable per category"}</b>{bars}</div>
<table>{"".join(rows)}</table>
<footer>{html.escape(APP_COPYRIGHT)}</footer>
</body></html>"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(doc)
    os.replace(tmp, path)
