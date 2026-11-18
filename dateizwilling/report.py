"""HTML- und CSV-Bericht der gefundenen Duplikate."""
from __future__ import annotations

import csv
import html
import os
import time

from . import APP_COPYRIGHT, APP_NAME, APP_VERSION
from .common import csv_safe, human_size, human_time
from .formats import category_of


def write_csv(path: str, groups: list[dict]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Gruppe", "Rolle", "Pfad", "Groesse (Bytes)", "Geaendert", "Kategorie",
                    "BLAKE2b-256", "Status"])
        for g in groups:
            for m in g["members"]:
                w.writerow([g["gid"], "Original" if m.get("keep") else "Duplikat", csv_safe(m["path"]),
                            g["size"], human_time(m["mtime_ns"]), category_of(m["path"]),
                            g["hash"], m.get("state", "open")])
    os.replace(tmp, path)


def write_html(path: str, groups: list[dict], stats: dict | None = None, lang: str = "de") -> None:
    de = lang == "de"
    stats = stats or {}
    wasted = sum(g["size"] * sum(1 for m in g["members"] if not m.get("keep")) for g in groups)
    rows = []
    for g in groups:
        n_dup = sum(1 for m in g["members"] if not m.get("keep"))
        rows.append(
            f'<tr class="grp"><td colspan="4">{"Gruppe" if de else "Group"} {g["gid"]} · '
            f'{len(g["members"])} {"Dateien" if de else "files"} · {human_size(g["size"], lang)} · '
            f'{"Ersparnis" if de else "Savings"} {human_size(g["size"] * n_dup, lang)}'
            f'<span class="h">{g["hash"][:16]}…</span></td></tr>')
        for m in g["members"]:
            role = ("Original" if m.get("keep") else ("Duplikat" if de else "Duplicate"))
            cls = "keep" if m.get("keep") else "dup"
            rows.append(
                f'<tr class="{cls}"><td>{role}</td><td>{html.escape(m["path"])}</td>'
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
</style></head><body>
<h1>{APP_NAME} {APP_VERSION}</h1>
<div class="sub">{"Bericht vom" if de else "Report from"} {time.strftime("%d.%m.%Y %H:%M")}</div>
<div class="cards">
<div class="card">{"Gruppen" if de else "Groups"}<b>{len(groups)}</b></div>
<div class="card">{"Duplikate" if de else "Duplicates"}<b>{sum(sum(1 for m in g["members"] if not m.get("keep")) for g in groups)}</b></div>
<div class="card">{"Einsparbar" if de else "Reclaimable"}<b>{human_size(wasted, lang)}</b></div>
<div class="card">{"Gescannte Dateien" if de else "Files scanned"}<b>{stats.get("files", "–")}</b></div>
</div>
<table>{"".join(rows)}</table>
<footer>{html.escape(APP_COPYRIGHT)}</footer>
</body></html>"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(doc)
    os.replace(tmp, path)
