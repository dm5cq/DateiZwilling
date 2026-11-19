"""Zusaetzliche Dialoge der Oberflaeche (2.0): Info, Lizenz, Haftungsausschluss,
Diagnose, Statistik, Archiv-Browser, Zeitplan. Als Mixin fuer gui.App."""
from __future__ import annotations

import json
import os
import platform
import sys
import time
import tkinter as tk
import zipfile
from tkinter import filedialog, ttk

from . import APP_BUILD_DATE, APP_NAME, APP_VERSION, scheduler
from .common import human_size, human_time
from .pathutil import open_with_default_app, resource_path, reveal_in_file_manager
from .report import CAT_NAMES, category_stats
from .state import J_DONE, J_PLANNED

LICENSE_FALLBACK = ("GNU GENERAL PUBLIC LICENSE, Version 3, 29 June 2007\n\n"
                    "Der vollstaendige Lizenztext liegt als Datei LICENSE bei bzw. unter "
                    "https://www.gnu.org/licenses/gpl-3.0.html")


class DialogsMixin:
    # ------------------------------------------------------------------ Hilfen
    def _center(self, win: tk.Toplevel) -> None:
        try:
            win.update_idletasks()
            w, h = win.winfo_reqwidth(), win.winfo_reqheight()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            x = max(0, min(sw - w, rx + (rw - w) // 2))
            y = max(0, min(sh - h - 40, ry + (rh - h) // 3))
            win.geometry(f"+{x}+{y}")
        except (tk.TclError, TypeError, ValueError):
            pass

    def _btn(self, parent, text, cmd, primary=False):
        c = self.c
        return tk.Button(parent, text=text, command=cmd, font=self.f_bold if primary else self.f_normal,
                         bg=c.accent if primary else c.field, fg=c.on_accent if primary else c.fg,
                         activebackground=c.accent_hover if primary else c.hover,
                         activeforeground=c.on_accent if primary else c.fg, relief="flat", bd=0,
                         padx=14, pady=5, cursor="hand2", highlightthickness=1,
                         highlightbackground=c.border, highlightcolor=c.accent)

    # ------------------------------------------------------------------ Info (A)
    def show_info(self) -> None:
        c, t = self.c, self.tr
        win = self._dialog(t("info_title"), None)
        win.resizable(False, False)
        body = tk.Frame(win, bg=c.panel)
        body.pack(fill="both", expand=True, padx=34, pady=(26, 8))
        try:
            png = resource_path(os.path.join("assets", "icon_96.png"))
            if os.path.exists(png):
                self._info_icon = tk.PhotoImage(file=png)
                tk.Label(body, image=self._info_icon, bg=c.panel).pack()
        except tk.TclError:
            pass
        tk.Label(body, text=APP_NAME, bg=c.panel, fg=c.accent, font=self.f_title).pack(pady=(8, 0))
        tk.Label(body, text=f"Version {APP_VERSION} · {APP_BUILD_DATE}", bg=c.panel, fg=c.muted,
                 font=self.f_normal).pack()
        tk.Label(body, text=t("info_short"), bg=c.panel, fg="#ffffff", font=self.f_normal,
                 wraplength=420, justify="center").pack(pady=(14, 14))
        grid = tk.Frame(body, bg=c.panel)
        grid.pack()
        rows = [(t("info_idea"), "Stefan J. Kaiser DM5CQ / OE8KKS"),
                (t("info_impl"), "Claude (Anthropic)"),
                (t("info_license"), "GNU General Public License v3.0")]
        for i, (k, v) in enumerate(rows):
            tk.Label(grid, text=k, bg=c.panel, fg=c.muted, font=self.f_small, anchor="e").grid(
                row=i, column=0, sticky="e", padx=(0, 12), pady=2)
            tk.Label(grid, text=v, bg=c.panel, fg="#ffffff", font=self.f_normal, anchor="w").grid(
                row=i, column=1, sticky="w", pady=2)
        tk.Label(body, text=t("info_risk"), bg=c.panel, fg=c.yellow, font=self.f_small).pack(pady=(14, 4))
        tk.Frame(win, bg=c.border, height=1).pack(fill="x", pady=(10, 0))
        bar = tk.Frame(win, bg=c.header)
        bar.pack(fill="x")
        inner = tk.Frame(bar, bg=c.header)
        inner.pack(fill="x", padx=14, pady=12)
        self._btn(inner, t("ok"), win.destroy, True).pack(side="right")
        self._btn(inner, t("btn_license"), self.show_license).pack(side="left")
        self._btn(inner, t("btn_disclaimer"), lambda: self.show_disclaimer(False)).pack(side="left", padx=6)
        self._btn(inner, t("btn_logs"), lambda: open_with_default_app(
            os.path.join(self.data_dir, "Protokolle"))).pack(side="left")
        self._center(win)

    def show_license(self) -> None:
        c, t = self.c, self.tr
        win = self._dialog(t("license_title"), "720x620")
        tk.Label(win, text=t("license_intro"), bg=c.panel, fg="#ffffff", font=self.f_normal,
                 wraplength=660, justify="left").pack(anchor="w", padx=18, pady=(16, 8))
        fr = tk.Frame(win, bg=c.panel)
        bar = tk.Frame(win, bg=c.header)
        bar.pack(side="bottom", fill="x")
        self._btn(bar, t("close"), win.destroy, True).pack(side="right", padx=14, pady=10)
        fr.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        txt = tk.Text(fr, bg=c.field, fg=c.fg, font=self.f_mono, relief="flat", wrap="word",
                      insertbackground=c.fg)
        sb = ttk.Scrollbar(fr, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        text = LICENSE_FALLBACK
        for cand in (resource_path(os.path.join("assets", "LICENSE.txt")), resource_path("LICENSE")):
            try:
                with open(cand, encoding="utf-8") as fh:
                    text = fh.read()
                break
            except OSError:
                continue
        txt.insert("1.0", text)
        txt.configure(state="disabled")

    def show_disclaimer(self, first_start: bool) -> None:
        c, t = self.c, self.tr
        win = self._dialog(t("disclaimer_title"), None)
        win.resizable(False, False)
        body = tk.Frame(win, bg=c.panel)
        body.pack(fill="both", expand=True, padx=26, pady=(22, 14))
        ic = tk.Canvas(body, width=46, height=46, bg=c.panel, highlightthickness=0)
        ic.create_oval(3, 3, 43, 43, fill=c.yellow, outline="")
        ic.create_text(23, 23, text="!", fill="#1e1e1e", font=(self.f_bold[0], int(self.f_bold[1] * 1.6), "bold"))
        ic.pack(side="left", anchor="n", padx=(0, 16))
        tk.Label(body, text=t("disclaimer_text"), bg=c.panel, fg="#ffffff", font=self.f_normal,
                 wraplength=470, justify="left").pack(side="left")
        tk.Frame(win, bg=c.border, height=1).pack(fill="x")
        bar = tk.Frame(win, bg=c.header)
        bar.pack(fill="x")

        def ok():
            if first_start:
                self.cfg["disclaimer_accepted"] = APP_VERSION
                from . import config
                config.save(self.data_dir, self.cfg)
            win.destroy()
        self._btn(bar, t("accept") if first_start else t("ok"), ok, True).pack(side="right", padx=14, pady=10)
        if first_start:
            self._btn(bar, t("btn_license"), self.show_license).pack(side="left", padx=14, pady=10)
            win.protocol("WM_DELETE_WINDOW", ok)
        self._center(win)
        if first_start:
            try:
                self.root.wait_window(win)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------ Diagnose (ST7)
    def export_diagnostics(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".zip",
            initialfile=f"DateiZwilling-Diagnose-{time.strftime('%Y%m%d-%H%M')}.zip",
            filetypes=[("ZIP", "*.zip")])
        if not path:
            return
        try:
            info = {
                "app": APP_NAME, "version": APP_VERSION, "build": APP_BUILD_DATE,
                "python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
                "frozen": bool(getattr(sys, "frozen", False)), "data_dir": self.data_dir,
                "runs": self.store.runs_list(limit=20), "cache_entries": self.store.cache_count(),
                "settings": {k: v for k, v in self.cfg.items() if k not in ("sources", "protected", "archive",
                                                                          "prefer", "avoid", "excludes")},
                "sources_count": len(self.cfg.get("sources", [])),
            }
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("system.json", json.dumps(info, indent=2, ensure_ascii=False, default=str))
                logdir = os.path.join(self.data_dir, "Protokolle")
                if os.path.isdir(logdir):
                    home = os.path.expanduser("~")
                    user = os.path.basename(home.rstrip("\\/"))
                    for f in os.listdir(logdir):
                        fp = os.path.join(logdir, f)
                        if os.path.isfile(fp) and os.path.getsize(fp) < 30 * 1024 * 1024:
                            with open(fp, encoding="utf-8", errors="replace") as fh:
                                text = fh.read()
                            # S10: Benutzerordner/-name in der Diagnose unkenntlich machen
                            text = text.replace(home, "~")
                            if len(user) > 2:
                                text = text.replace(user, "<Benutzer>")
                            z.writestr("Protokolle/" + f, text)
            self.info(self.tr("diag_done", path=path))
        except OSError as exc:
            self.info(str(exc), "error")

    # ------------------------------------------------------------------ Statistik (F6)
    def show_stats(self) -> None:
        c, t, lang = self.c, self.tr, self.cfg["lang"]
        cats = category_stats(self.groups)
        win = self._dialog(t("stats_title"), "760x540")
        bar = tk.Frame(win, bg=c.header)
        bar.pack(side="bottom", fill="x")
        self._btn(bar, t("close"), win.destroy, True).pack(side="right", padx=14, pady=10)
        if not cats:
            tk.Label(win, text=t("stats_empty"), bg=c.panel, fg=c.fg, font=self.f_normal).pack(pady=40)
            return
        dups = sum(x["duplicates"] for x in cats)
        total = sum(x["wasted"] for x in cats)
        tk.Label(win, text=t("stats_total", dups=dups, size=human_size(total, lang),
                             folders=len(getattr(self, "folder_groups", [])),
                             similar=sum(1 for g in self.groups if g.get("kind") == "similar")),
                 bg=c.panel, fg="#ffffff", font=self.f_bold, wraplength=700, justify="left").pack(
            anchor="w", padx=18, pady=(16, 8))
        cv = tk.Canvas(win, bg=c.panel, highlightthickness=0)
        cv.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        names = CAT_NAMES.get(lang, CAT_NAMES["de"])
        top = max(x["wasted"] for x in cats) or 1

        def draw(_e=None):
            cv.delete("all")
            w = max(400, cv.winfo_width())
            rowh = max(26, int(self.row_h * 1.1))
            label_w, val_w = 170, 170
            bar_w = w - label_w - val_w - 20
            for i, x in enumerate(cats):
                y = 8 + i * rowh
                cv.create_text(0, y + rowh / 2, text=names.get(x["category"], x["category"]), anchor="w",
                               fill=c.fg, font=self.f_normal)
                cv.create_rectangle(label_w, y + 6, label_w + bar_w, y + rowh - 6, fill=c.field, outline="")
                bw = max(3, int(bar_w * x["wasted"] / top))
                cv.create_rectangle(label_w, y + 6, label_w + bw, y + rowh - 6, fill=c.accent, outline="")
                cv.create_text(w - 4, y + rowh / 2, anchor="e", fill=c.muted, font=self.f_small,
                               text=f"{human_size(x['wasted'], lang)} · {x['duplicates']}")
        cv.bind("<Configure>", draw)
        win.after(50, draw)

    # ------------------------------------------------------------------ Archiv-Browser (F4/S5)
    def show_archive_browser(self) -> None:
        if self.busy_kind:
            self.info(self.tr("busy"))
            return
        c, t, lang = self.c, self.tr, self.cfg["lang"]
        win = self._dialog(t("br_title"), "1100x680")
        bar = tk.Frame(win, bg=c.header)
        bar.pack(side="bottom", fill="x")
        paned = ttk.PanedWindow(win, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=12, pady=12)

        left = ttk.Frame(paned, style="Panel.TFrame")
        ttk.Label(left, text=t("br_runs"), style="Section.TLabel").pack(anchor="w")
        runs_tv = ttk.Treeview(left, columns=("date", "kind", "n", "state"), show="headings", selectmode="browse")
        for col, txt, wd in (("date", t("col_date"), 135), ("kind", "", 95), ("n", "#", 50), ("state", "", 80)):
            runs_tv.heading(col, text=txt)
            runs_tv.column(col, width=wd, stretch=col == "date")
        runs_tv.pack(fill="both", expand=True, pady=(4, 0))
        paned.add(left, weight=1)

        right = ttk.Frame(paned, style="Panel.TFrame")
        top = ttk.Frame(right, style="Panel.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=t("br_files"), style="Section.TLabel").pack(side="left")
        q = tk.StringVar()
        ttk.Entry(top, textvariable=q, width=30).pack(side="right")
        ttk.Label(top, text=t("search"), style="Panel.TLabel").pack(side="right", padx=4)
        files_tv = ttk.Treeview(right, columns=("orig", "size", "status"), show="headings", selectmode="extended")
        for col, txt, wd in (("orig", t("br_original"), 520), ("size", t("col_size"), 90),
                             ("status", t("br_status"), 110)):
            files_tv.heading(col, text=txt)
            files_tv.column(col, width=wd, stretch=col == "orig")
        sb = ttk.Scrollbar(right, orient="vertical", command=files_tv.yview)
        files_tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", pady=(4, 0))
        files_tv.pack(fill="both", expand=True, pady=(4, 0))
        paned.add(right, weight=3)

        runs = self.store.runs_list(None, 500)
        entries_cache: dict[int, list[dict]] = {}
        st_names = {"done": "st_done", "undone": "st_undone", "purged": "st_purged", "skipped": "st_skipped",
                    "failed": "st_failed", "planned": "st_planned", "copying": "st_planned", "copied": "st_planned"}

        for r in runs:
            n = len(self.store.journal_entries(r["id"]))
            runs_tv.insert("", "end", iid=str(r["id"]), values=(
                human_time(r["created"], lang), t("br_kind_" + r["kind"]) if r["kind"] in ("archive", "undo")
                else r["kind"], n, r["state"]))

        def cur_run() -> dict | None:
            sel = runs_tv.selection()
            return next((r for r in runs if str(r["id"]) == sel[0]), None) if sel else None

        def fill(*_):
            files_tv.delete(*files_tv.get_children())
            r = cur_run()
            if not r:
                return
            ents = entries_cache.setdefault(r["id"], self.store.journal_entries(r["id"]))
            needle = q.get().strip().lower()
            shown = 0
            for e in ents:
                orig = e["src"] if r["kind"] == "archive" else e["dst"]
                if needle and needle not in orig.lower():
                    continue
                files_tv.insert("", "end", iid=str(e["id"]), values=(
                    orig + ("  (+)" if e["sidecar"] else ""),
                    human_size(e["size"], lang) if e["size"] else "",
                    t(st_names.get(e["state"], "st_failed"))))
                shown += 1
                if shown >= 20000:
                    break
            update_buttons()

        def update_buttons(*_):
            r = cur_run()
            arch = bool(r and r["kind"] == "archive")
            for b, ok in ((b_restore, arch and bool(files_tv.selection())), (b_undo, arch),
                          (b_resume, bool(r and r["state"] == "running")), (b_reveal, bool(files_tv.selection()))):
                b.configure(state="normal" if ok else "disabled")

        def selected_ids() -> list[int]:
            r = cur_run()
            ents = {e["id"]: e for e in entries_cache.get(r["id"], [])} if r else {}
            return [int(i) for i in files_tv.selection() if int(i) in ents and ents[int(i)]["state"] == J_DONE]

        def restore():
            r = cur_run()
            ids = selected_ids()
            if not r or not ids or not self.ask_yes_no(t("br_restore"), t("restore_confirm", n=len(ids))):
                return
            win.destroy()
            self._run_undo(r, ids)

        def undo_run():
            r = cur_run()
            if not r or not self.ask_yes_no(APP_NAME, t("undo_confirm", id=r["id"])):
                return
            win.destroy()
            self._run_undo(r, None)

        def resume():
            r = cur_run()
            if r:
                win.destroy()
                self._resume_run(r)

        def reveal():
            r = cur_run()
            sel = files_tv.selection()
            if r and sel:
                e = next((x for x in entries_cache.get(r["id"], []) if str(x["id"]) == sel[0]), None)
                if e:
                    reveal_in_file_manager(e["dst"] if r["kind"] == "archive" else e["src"])

        def do_import():
            d = filedialog.askdirectory(parent=win, mustexist=True)
            if not d:
                return
            try:
                from .archiver import Archiver
                res = Archiver(self.store, self._new_control()).import_archive(d)
                self.info(t("import_done", **res), parent=win)
            except OSError as exc:
                self.info(str(exc), "error", parent=win)
            win.destroy()
            self.show_archive_browser()

        b_restore = self._btn(bar, t("br_restore"), restore, True)
        b_restore.pack(side="right", padx=(6, 14), pady=10)
        b_undo = self._btn(bar, t("br_undo_run"), undo_run)
        b_undo.pack(side="right", padx=6, pady=10)
        b_resume = self._btn(bar, t("br_resume"), resume)
        b_resume.pack(side="right", padx=6, pady=10)
        b_reveal = self._btn(bar, t("br_reveal"), reveal)
        b_reveal.pack(side="left", padx=(14, 6), pady=10)
        self._btn(bar, t("br_import"), do_import).pack(side="left", padx=6, pady=10)
        runs_tv.bind("<<TreeviewSelect>>", fill)
        files_tv.bind("<<TreeviewSelect>>", update_buttons)
        q.trace_add("write", fill)
        if runs:
            runs_tv.selection_set(str(runs[0]["id"]))
            fill()
        update_buttons()

    # ------------------------------------------------------------------ Zeitplan (F7)
    def show_schedule(self) -> None:
        c, t = self.c, self.tr
        self._sync_cfg()
        win = self._dialog(t("sch_title"), None)
        win.resizable(False, False)
        body = ttk.Frame(win, style="Panel.TFrame", padding=20)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=t("sch_info"), bg=c.panel, fg="#ffffff", font=self.f_normal, wraplength=520,
                 justify="left").pack(anchor="w")
        status = tk.StringVar(value=t("sch_active") if scheduler.exists() else t("sch_none"))
        tk.Label(body, textvariable=status, bg=c.panel, fg=c.accent, font=self.f_bold).pack(anchor="w", pady=(10, 8))
        mode = tk.StringVar(value="weekly")
        row = ttk.Frame(body, style="Panel.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Radiobutton(row, text=t("sch_daily"), value="daily", variable=mode).pack(side="left")
        ttk.Radiobutton(row, text=t("sch_weekly"), value="weekly", variable=mode).pack(side="left", padx=(16, 6))
        days = t("weekdays").split(",")
        day_cb = ttk.Combobox(row, state="readonly", values=days, width=12)
        day_cb.current(6)
        day_cb.pack(side="left")
        row2 = ttk.Frame(body, style="Panel.TFrame")
        row2.pack(fill="x", pady=4)
        ttk.Label(row2, text=t("sch_time"), style="Panel.TLabel").pack(side="left")
        tm = tk.StringVar(value="19:42")
        ttk.Entry(row2, textvariable=tm, width=8).pack(side="left", padx=8)
        bar = tk.Frame(win, bg=c.header)
        bar.pack(fill="x")

        def create():
            errs = [e for e in self._validate_for_schedule()]
            if errs:
                self.info("\n".join(errs), "warning", parent=win)
                return
            try:
                ok, msg = scheduler.create(self.data_dir, self.cfg["sources"], self.cfg["archive"],
                                           mode.get() == "weekly", day_cb.current(), tm.get().strip())
            except (ValueError, OSError) as exc:
                ok, msg = False, str(exc)
            if ok:
                status.set(t("sch_active"))
                self.info(t("sch_ok"), parent=win)
            else:
                self.info(t("sch_fail", msg=msg), "error", parent=win)

        def remove():
            scheduler.remove()
            status.set(t("sch_none"))
            self.info(t("sch_removed"), parent=win)
        self._btn(bar, t("sch_create"), create, True).pack(side="right", padx=(6, 14), pady=10)
        self._btn(bar, t("sch_remove"), remove).pack(side="right", padx=6, pady=10)
        self._btn(bar, t("close"), win.destroy).pack(side="left", padx=14, pady=10)
        self._center(win)

    def _validate_for_schedule(self) -> list[str]:
        from .scanner import validate_options
        return [self.tr.error(e) for e in validate_options(self._options())]
