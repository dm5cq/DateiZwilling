"""Grafische Oberflaeche (Tkinter) im Stil von BildZwilling / FotoRahmen:
Dunkelgrau, Orange, Weiss – graue Titelleiste unter Windows.
"""
from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import font as tkfont

from . import APP_COPYRIGHT, APP_COPYRIGHT_EN, APP_NAME, APP_VERSION, config
from .archiver import Archiver, NeedsAttention, recover_all
from .gui_extra import DialogsMixin
from .pathutil import KeepAwake, cloud_sync_kind, is_within, risky_source
from .preview import make_preview
from .common import Cancelled, Control, human_duration, human_size, human_time
from .formats import CATEGORY_ORDER, PREVIEWABLE, category_of, ext_of
from .i18n import Tr
from .pathutil import (IS_MAC, IS_WIN, fs, is_network_path, open_with_default_app,
                       resource_path, reveal_in_file_manager)
from .report import write_csv, write_html
from .scanner import ScanOptions, Scanner, validate_options
from .state import J_DONE, J_PLANNED, J_SKIPPED, Store

try:  # Vorschau ist optional – ohne Pillow laeuft alles andere weiter
    from PIL import Image, ImageOps, ImageTk  # type: ignore
except Exception:  # pragma: no cover
    Image = ImageOps = ImageTk = None  # type: ignore

log = logging.getLogger("dateizwilling.gui")

PAGE_SIZE = 1000


class Palette:
    def __init__(self, high_contrast: bool):
        if high_contrast:
            self.bg, self.panel, self.header, self.field = "#000000", "#000000", "#000000", "#000000"
            self.border, self.hover = "#ffffff", "#333333"
            self.fg, self.muted = "#ffffff", "#ffffff"
            self.accent, self.accent_hover, self.on_accent = "#ffff00", "#ffff66", "#000000"
            self.green, self.red, self.yellow, self.blue = "#00ff00", "#ff4040", "#ffff00", "#00ffff"
            self.group_bg = "#1a1a1a"
        else:
            self.bg, self.panel, self.header, self.field = "#2b2b2b", "#333333", "#232323", "#3c3c3c"
            self.border, self.hover = "#4a4a4a", "#4a4a4a"
            self.fg, self.muted = "#f0f0f0", "#a8a8a8"
            self.accent, self.accent_hover, self.on_accent = "#f28c28", "#ff9d3d", "#1e1e1e"
            self.green, self.red, self.yellow, self.blue = "#5cb85c", "#d9534f", "#f0ad4e", "#5bc0de"
            self.group_bg = "#353535"


def style_titlebar(win: tk.Misc, color: str, text: str = "#ffffff") -> None:
    """Dunkelgraue Titelleiste mit weisser Schrift unter Windows 10/11 (DWM).
    Wird nach dem Anzeigen des Fensters erneut angewendet, damit auch
    Dialoge (Info, Einstellungen …) zuverlaessig grau werden."""
    if not IS_WIN:
        return

    def apply() -> None:
        try:
            import ctypes
            if not win.winfo_exists():
                return
            win.update_idletasks()
            try:
                hwnd = int(win.wm_frame(), 16)  # type: ignore[attr-defined]
            except Exception:
                hwnd = 0
            if not hwnd:
                hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
            dwm = ctypes.windll.dwmapi
            dark = ctypes.c_int(1)
            for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (neu/alt)
                if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(dark), ctypes.sizeof(dark)) == 0:
                    break

            def ref(hx: str) -> ctypes.c_int:
                r, g, b = int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16)
                return ctypes.c_int(r | (g << 8) | (b << 16))
            cap, txt, border = ref(color), ref(text), ref(color)
            dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(cap), 4)     # Titelleiste
            dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(txt), 4)     # Titeltext
            dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border), 4)  # Rahmen
            # Rahmen neu zeichnen lassen (sonst bleibt die Leiste bis zum Fokuswechsel weiss)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)
        except Exception:
            pass
    apply()
    try:
        win.after(60, apply)
        win.bind("<Map>", lambda e: win.after(10, apply) if e.widget is win else None, add="+")
    except Exception:
        pass


def dark_dialog(parent: tk.Misc, c: "Palette", font: tuple, bold: tuple, title: str, text: str,
                kind: str = "info", buttons: tuple = (("ok", "OK"),), default: str = "ok",
                cancel_value=None):
    """Eigener, dunkler Meldungsdialog (statt der weissen Windows-Meldungsfenster).
    buttons: ((rueckgabewert, beschriftung), …) – der Standardknopf ist orange."""
    win = tk.Toplevel(parent)
    win.withdraw()
    win.title(title)
    win.configure(bg=c.panel)
    win.resizable(False, False)
    try:
        win.transient(parent)
    except tk.TclError:
        pass
    result = {"v": cancel_value}

    def done(v) -> None:
        result["v"] = v
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    body = tk.Frame(win, bg=c.panel)
    body.pack(fill="both", expand=True, padx=22, pady=(20, 12))
    sym_color = {"info": c.blue, "question": c.accent, "warning": c.yellow, "error": c.red}.get(kind, c.accent)
    sym = {"info": "i", "question": "?", "warning": "!", "error": "✕"}.get(kind, "i")
    ic = tk.Canvas(body, width=46, height=46, bg=c.panel, highlightthickness=0)
    ic.create_oval(3, 3, 43, 43, fill=sym_color, outline="")
    ic.create_text(23, 23, text=sym, fill=c.on_accent if kind == "question" else "#ffffff",
                   font=(bold[0], int(bold[1] * 1.6), "bold"))
    ic.pack(side="left", anchor="n", padx=(0, 16))
    tk.Label(body, text=text, bg=c.panel, fg=c.fg, font=font, justify="left", anchor="w",
             wraplength=480).pack(side="left", fill="both", expand=True)
    sep = tk.Frame(win, bg=c.border, height=1)
    sep.pack(fill="x")
    row = tk.Frame(win, bg=c.header)
    row.pack(fill="x")
    focus_btn = None
    for value, label in reversed(buttons):
        primary = value == default
        b = tk.Button(row, text=label, command=lambda v=value: done(v), font=bold if primary else font,
                      bg=c.accent if primary else c.field, fg=c.on_accent if primary else c.fg,
                      activebackground=c.accent_hover if primary else c.hover,
                      activeforeground=c.on_accent if primary else c.fg,
                      relief="flat", bd=0, padx=18, pady=6, cursor="hand2",
                      highlightthickness=1, highlightbackground=c.border, highlightcolor=c.accent)
        b.pack(side="right", padx=(8, 0), pady=12)
        if primary:
            focus_btn = b
    tk.Frame(row, bg=c.header, width=10).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", lambda: done(cancel_value))
    win.bind("<Escape>", lambda e: done(cancel_value))
    win.bind("<Return>", lambda e: done(default))
    try:
        win.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        if pw > 50:
            win.geometry(f"+{px + max(0, (pw - w) // 2)}+{py + max(0, (ph - h) // 3)}")
    except (tk.TclError, TypeError, ValueError):
        pass
    win.deiconify()
    style_titlebar(win, c.header)
    win.after(60, lambda: _safe_grab(win))
    if focus_btn is not None:
        focus_btn.focus_set()
    try:
        parent.wait_window(win)
    except tk.TclError:
        pass
    return result["v"]


class ScrollFrame:
    """Senkrecht scrollbarer Bereich (Seitenleiste) – Bildlaufleiste erscheint
    nur, wenn der Inhalt nicht in das Fenster passt."""

    def __init__(self, parent: tk.Misc, bg: str):
        self.canvas = tk.Canvas(parent, bg=bg, highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Panel.TFrame")
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind_all("<MouseWheel>", self._wheel, add="+")

    def _on_inner(self, _e=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_bar()

    def _on_canvas(self, e) -> None:
        self.canvas.itemconfigure(self._win, width=e.width)
        self._update_bar()

    def _update_bar(self) -> None:
        try:
            need = self.inner.winfo_reqheight() > self.canvas.winfo_height() + 2
            if need and not self.vsb.winfo_ismapped():
                self.vsb.pack(side="right", fill="y", before=self.canvas)
            elif not need and self.vsb.winfo_ismapped():
                self.vsb.pack_forget()
                self.canvas.yview_moveto(0)
        except (tk.TclError, TypeError):
            pass

    def _wheel(self, e) -> None:
        try:
            w = self.canvas.winfo_containing(e.x_root, e.y_root)
            if w is None or not str(w).startswith(str(self.canvas)) or isinstance(w, tk.Listbox):
                return
            if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
                return
            step = -int(e.delta / 120) if IS_WIN else -int(e.delta)
            self.canvas.yview_scroll(step or (-1 if e.delta > 0 else 1), "units")
        except (tk.TclError, KeyError, AttributeError, TypeError):
            pass


def speak(text: str) -> None:
    """Sprachausgabe (Windows SAPI / macOS say) im Hintergrund."""
    def run() -> None:
        try:
            if IS_WIN:
                safe = text.replace("'", "''")
                cmd = ("Add-Type -AssemblyName System.Speech; "
                       "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('%s')" % safe)
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                               creationflags=0x08000000, timeout=60, capture_output=True)
            elif IS_MAC:
                subprocess.run(["say", text], timeout=60, capture_output=True)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


class QueueLogHandler(logging.Handler):
    def __init__(self, q: "queue.Queue"):
        super().__init__(logging.INFO)
        self.q = q
        self.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.q.put_nowait(("log", self.format(record)))
        except Exception:
            pass


class App(DialogsMixin):
    def __init__(self, root: tk.Tk, store: Store, data_dir: str):
        self.root = root
        self.store = store
        self.data_dir = data_dir
        self.cfg = config.load(data_dir)
        self.tr = Tr(self.cfg["lang"])
        self.q: queue.Queue = queue.Queue()
        self.control: Control | None = None
        self.worker: threading.Thread | None = None
        self.busy_kind: str | None = None
        self.session_id: int | None = None
        self.session_stats: dict = {}
        self.groups: list[dict] = []
        self.group_by_id: dict[int, dict] = {}
        self.iid_member: dict[str, tuple[int, int]] = {}
        self.iid_folder: dict[str, tuple[int, int]] = {}
        self.folder_groups: list[dict] = []
        self.view = "same"
        self.page = 0
        self._preview_token = 0
        self.populated: set[int] = set()
        self._img_refs: list = []
        self._log_lines: list[str] = []
        self._last_progress: dict | None = None
        self.log_handler = QueueLogHandler(self.q)
        logging.getLogger("dateizwilling").addHandler(self.log_handler)

        root.title(f"{APP_NAME} {APP_VERSION}")
        self._fit_window(root)
        self._set_icon(root)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.report_callback_exception = self._tk_exception
        self.build_ui()
        root.after(100, self.poll)
        root.after(400, self.startup_checks)

    # ================================================================ Aufbau
    def _fit_window(self, root: tk.Tk) -> None:
        """Fenster an den Bildschirm anpassen: gespeicherte Groesse nur, wenn sie
        auf den aktuellen Bildschirm passt – sonst 92 % der Flaeche, zentriert.
        Kleine Bildschirme (Hoehe < 900 px) starten maximiert."""
        try:
            sw, sh = int(root.winfo_screenwidth()), int(root.winfo_screenheight())
        except (tk.TclError, TypeError, ValueError):
            sw, sh = 1920, 1080
        maxw, maxh = int(sw * 0.96), int(sh * 0.90)
        root.minsize(min(900, maxw), min(600, maxh))
        geo = str(self.cfg.get("geometry") or "")
        w = h = x = y = None
        try:
            size, _, pos = geo.partition("+")
            w, h = (int(v) for v in size.split("x"))
            if pos:
                x, y = (int(v) for v in pos.split("+")[:2])
        except ValueError:
            w = h = None
        if not w or not h or w > maxw or h > maxh:
            w, h = min(1440, int(sw * 0.92)), min(920, int(sh * 0.86))
            x, y = None, None
        if x is None or y is None or x < -20 or y < -20 or x + 100 > sw or y + 60 > sh:
            x, y = max(0, (sw - w) // 2), max(0, (sh - h) // 3)
        try:
            root.geometry(f"{w}x{h}+{x}+{y}")
            if IS_WIN and (sh < 900 or self.cfg.get("maximized")):
                root.state("zoomed")
        except tk.TclError:
            pass

    def _set_icon(self, win: tk.Misc) -> None:
        try:
            png = resource_path(os.path.join("assets", "icon.png"))
            if os.path.exists(png):
                self._icon_img = tk.PhotoImage(file=png)
                win.iconphoto(True, self._icon_img)  # type: ignore[attr-defined]
            ico = resource_path(os.path.join("assets", "icon.ico"))
            if IS_WIN and os.path.exists(ico):
                win.iconbitmap(default=ico)  # type: ignore[attr-defined]
        except tk.TclError:
            pass

    def _fonts(self) -> None:
        scale = float(self.cfg.get("font_scale", 1.0))
        base = 10 if IS_WIN else 13
        size = max(8, int(round(base * scale)))
        family = "Segoe UI" if IS_WIN else ("SF Pro Text" if IS_MAC else "DejaVu Sans")
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(family=family, size=size)
            except tk.TclError:
                pass
        self.f_normal = (family, size)
        self.f_bold = (family, size, "bold")
        self.f_small = (family, max(7, size - 1))
        self.f_title = (family, int(size * 1.8), "bold")
        self.f_mono = ("Consolas" if IS_WIN else "Menlo", max(7, size - 1))
        self.row_h = int(size * 2.3)

    def _style(self) -> None:
        c = self.c
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", background=c.bg, foreground=c.fg, fieldbackground=c.field,
                     bordercolor=c.border, lightcolor=c.panel, darkcolor=c.panel,
                     troughcolor=c.field, focuscolor=c.accent, selectbackground=c.accent,
                     selectforeground=c.on_accent, insertcolor=c.fg, font=self.f_normal)
        st.configure("TFrame", background=c.bg)
        st.configure("Panel.TFrame", background=c.panel)
        st.configure("Header.TFrame", background=c.header)
        st.configure("TLabel", background=c.bg, foreground=c.fg)
        st.configure("Panel.TLabel", background=c.panel, foreground=c.fg)
        st.configure("Muted.TLabel", background=c.panel, foreground=c.muted, font=self.f_small)
        st.configure("Section.TLabel", background=c.panel, foreground=c.accent, font=self.f_bold)
        st.configure("Header.TLabel", background=c.header, foreground=c.muted)
        st.configure("Title.TLabel", background=c.header, foreground=c.accent, font=self.f_title)
        st.configure("Status.TLabel", background=c.header, foreground=c.fg)
        st.configure("TButton", background=c.field, foreground=c.fg, padding=(10, 5),
                     borderwidth=1, relief="flat")
        st.map("TButton", background=[("disabled", c.panel), ("active", c.hover)],
               foreground=[("disabled", c.muted)])
        st.configure("Accent.TButton", background=c.accent, foreground=c.on_accent,
                     font=self.f_bold, padding=(12, 8))
        st.map("Accent.TButton", background=[("disabled", c.field), ("active", c.accent_hover)],
               foreground=[("disabled", c.muted)])
        st.configure("Header.TButton", background=c.header, foreground=c.fg, padding=(10, 4))
        st.map("Header.TButton", background=[("active", c.hover)])
        st.configure("Danger.TButton", background=c.field, foreground=c.red)
        st.map("Danger.TButton", background=[("active", c.hover)])
        st.configure("Treeview", background=c.field, fieldbackground=c.field, foreground=c.fg,
                     rowheight=self.row_h, borderwidth=0)
        st.map("Treeview", background=[("selected", c.accent)], foreground=[("selected", c.on_accent)])
        st.configure("Treeview.Heading", background=c.panel, foreground=c.fg, relief="flat",
                     font=self.f_bold)
        st.map("Treeview.Heading", background=[("active", c.hover)])
        for w in ("TCheckbutton", "TRadiobutton"):
            st.configure(w, background=c.panel, foreground=c.fg, focuscolor=c.panel,
                         indicatorbackground=c.field, indicatorforeground="#ffffff",
                         indicatorcolor=c.field, upperbordercolor=c.border,
                         lowerbordercolor=c.border, indicatormargin=(0, 0, 6, 0))
            st.map(w,
                   indicatorbackground=[("disabled", c.panel), ("pressed", c.hover),
                                        ("selected", c.accent), ("!selected", c.field)],
                   indicatorcolor=[("selected", c.accent), ("!selected", c.field)],
                   indicatorforeground=[("selected", "#ffffff"), ("!selected", c.field)],
                   upperbordercolor=[("selected", c.accent), ("active", c.accent)],
                   lowerbordercolor=[("selected", c.accent), ("active", c.accent)],
                   background=[("active", c.panel)], foreground=[("disabled", c.muted)])
        st.configure("TCombobox", fieldbackground=c.field, background=c.field, foreground=c.fg,
                     arrowcolor=c.fg, selectbackground=c.field, selectforeground=c.fg)
        st.map("TCombobox", fieldbackground=[("readonly", c.field)], foreground=[("readonly", c.fg)],
               selectbackground=[("readonly", c.field)], selectforeground=[("readonly", c.fg)])
        st.configure("TEntry", fieldbackground=c.field, foreground=c.fg, insertcolor=c.fg,
                     bordercolor=c.border, lightcolor=c.field, darkcolor=c.field)
        st.map("TEntry", bordercolor=[("focus", c.accent)], lightcolor=[("focus", c.accent)])
        st.configure("TSpinbox", fieldbackground=c.field, foreground=c.fg, arrowcolor=c.fg,
                     background=c.field)
        st.configure("Horizontal.TProgressbar", background=c.accent, troughcolor=c.field,
                     bordercolor=c.border, lightcolor=c.accent, darkcolor=c.accent)
        st.configure("Vertical.TScrollbar", background=c.panel, troughcolor=c.bg, arrowcolor=c.fg,
                     bordercolor=c.bg)
        st.configure("Horizontal.TScrollbar", background=c.panel, troughcolor=c.bg, arrowcolor=c.fg,
                     bordercolor=c.bg)
        st.configure("TPanedwindow", background=c.bg)
        st.configure("Sash", sashthickness=6, gripcount=0, background=c.border)
        self.root.option_add("*TCombobox*Listbox.background", c.field)
        self.root.option_add("*TCombobox*Listbox.foreground", c.fg)
        self.root.option_add("*TCombobox*Listbox.selectBackground", c.accent)
        self.root.option_add("*TCombobox*Listbox.selectForeground", c.on_accent)
        self.root.configure(background=c.bg)

    def _listbox(self, parent: tk.Misc, height: int = 4) -> tk.Listbox:
        c = self.c
        return tk.Listbox(parent, height=height, bg=c.field, fg=c.fg, selectbackground=c.accent,
                          selectforeground=c.on_accent, highlightthickness=1,
                          highlightbackground=c.border, highlightcolor=c.accent, relief="flat",
                          activestyle="none", font=self.f_small, exportselection=False)

    def build_ui(self) -> None:
        for w in self.root.winfo_children():
            w.destroy()
        self.tr = Tr(self.cfg["lang"])
        self.c = Palette(bool(self.cfg.get("high_contrast")))
        self._fonts()
        self._style()
        t, c = self.tr, self.c

        # ---------- Kopfzeile
        head = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 10))
        head.pack(fill="x")
        ttk.Button(head, text=t("info"), style="Header.TButton", command=self.show_info).pack(side="right")
        ttk.Button(head, text=t("settings"), style="Header.TButton",
                   command=self.show_settings).pack(side="right", padx=4)
        ttk.Button(head, text=t("hdr_schedule"), style="Header.TButton",
                   command=self.show_schedule).pack(side="right", padx=4)
        ttk.Button(head, text=t("hdr_stats"), style="Header.TButton",
                   command=self.show_stats).pack(side="right", padx=4)
        ttk.Button(head, text=t("hdr_archive"), style="Header.TButton",
                   command=self.show_archive_browser).pack(side="right", padx=4)
        self.lang_btn = ttk.Button(head, text="EN" if self.cfg["lang"] == "de" else "DE",
                                   style="Header.TButton", command=self.toggle_lang, width=4)
        self.lang_btn.pack(side="right", padx=4)
        try:
            png = resource_path(os.path.join("assets", "icon_48.png"))
            if os.path.exists(png):
                self._head_icon = tk.PhotoImage(file=png)
                ttk.Label(head, image=self._head_icon, style="Header.TLabel").pack(side="left", padx=(0, 10))
        except tk.TclError:
            pass
        titles = ttk.Frame(head, style="Header.TFrame")
        titles.pack(side="left")
        ttk.Label(titles, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(titles, text=t("subtitle"), style="Header.TLabel").pack(anchor="w")

        # ---------- Statuszeile (unten)
        status = ttk.Frame(self.root, style="Header.TFrame", padding=(12, 6))
        status.pack(side="bottom", fill="x")
        self.progress = ttk.Progressbar(status, mode="determinate", length=320, maximum=100)
        self.progress.pack(side="left")
        self.status_var = tk.StringVar(value=t("ready"))
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").pack(side="left", padx=12)
        self.log_btn = ttk.Button(status, text=t("log") + " ▴", style="Header.TButton",
                                  command=self.toggle_log)
        self.log_btn.pack(side="right")
        self.rate_var = tk.StringVar(value="")
        ttk.Label(status, textvariable=self.rate_var, style="Header.TLabel").pack(side="right", padx=12)

        self.log_frame = ttk.Frame(self.root, style="Panel.TFrame")
        self.log_text = tk.Text(self.log_frame, height=9, bg=c.field, fg=c.fg, insertbackground=c.fg,
                                relief="flat", font=self.f_mono, wrap="none", state="disabled")
        lsb = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=lsb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        lsb.pack(side="right", fill="y")
        self.log_visible = False
        if self._log_lines:
            self._append_log("\n".join(self._log_lines[-500:]), rebuild=True)

        # ---------- Hauptbereich
        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True)
        side = ttk.Frame(body, style="Panel.TFrame", padding=(12, 10, 6, 10), width=345)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self._build_sidebar(side)
        main = ttk.Frame(body, padding=(10, 8, 10, 4))
        main.pack(side="left", fill="both", expand=True)
        self._build_main(main)

        style_titlebar(self.root, c.header)
        self._bind_keys()
        self._refresh_tree()
        self._set_busy(self.busy_kind)

    def _build_sidebar(self, outer: ttk.Frame) -> None:
        t = self.tr
        # fester Bereich unten: immer sichtbar, egal wie klein das Fenster ist
        bottom = ttk.Frame(outer, style="Panel.TFrame")
        bottom.pack(side="bottom", fill="x")
        self.scan_btn = ttk.Button(bottom, text=t("start_scan"), style="Accent.TButton", command=self.start_scan)
        self.scan_btn.pack(fill="x", pady=(8, 4))
        ctl = ttk.Frame(bottom, style="Panel.TFrame")
        ctl.pack(fill="x")
        self.pause_btn = ttk.Button(ctl, text=t("pause"), command=self.toggle_pause)
        self.pause_btn.pack(side="left", fill="x", expand=True)
        self.cancel_btn = ttk.Button(ctl, text=t("cancel"), style="Danger.TButton", command=self.cancel_work)
        self.cancel_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
        copy = APP_COPYRIGHT if self.cfg["lang"] == "de" else APP_COPYRIGHT_EN
        ttk.Label(bottom, text=copy, style="Muted.TLabel", wraplength=300, justify="left").pack(anchor="w", pady=(8, 0))
        # scrollbarer Bereich oben
        self.side_scroll = ScrollFrame(outer, self.c.panel)
        side = self.side_scroll.inner
        ttk.Label(side, text=t("sources"), style="Section.TLabel").pack(anchor="w")
        self.src_list = self._listbox(side, 5)
        self.src_list.pack(fill="x", pady=(4, 2))
        self._enable_drop(self.src_list)
        for s in self.cfg["sources"]:
            self.src_list.insert("end", s)
        row = ttk.Frame(side, style="Panel.TFrame")
        row.pack(fill="x")
        ttk.Button(row, text=t("add"), command=lambda: self._add_folder(self.src_list, "sources")).pack(side="left")
        ttk.Button(row, text=t("remove"), command=lambda: self._remove_folder(self.src_list, "sources")).pack(side="left", padx=4)
        ttk.Button(row, text=t("down"), width=3, command=lambda: self._move_src(1)).pack(side="right")
        ttk.Button(row, text=t("up"), width=3, command=lambda: self._move_src(-1)).pack(side="right", padx=4)

        ttk.Label(side, text=t("archive"), style="Section.TLabel").pack(anchor="w", pady=(14, 0))
        arow = ttk.Frame(side, style="Panel.TFrame")
        arow.pack(fill="x", pady=4)
        self.archive_var = tk.StringVar(value=self.cfg["archive"])
        arch_entry = ttk.Entry(arow, textvariable=self.archive_var)
        arch_entry.pack(side="left", fill="x", expand=True)
        self._enable_drop(arch_entry, "entry")
        ttk.Button(arow, text=t("browse"), command=self._choose_archive).pack(side="left", padx=(4, 0))

        ttk.Label(side, text=t("protected"), style="Section.TLabel").pack(anchor="w", pady=(10, 0))
        self.prot_list = self._listbox(side, 3)
        self.prot_list.pack(fill="x", pady=(4, 2))
        self._enable_drop(self.prot_list)
        for s in self.cfg["protected"]:
            self.prot_list.insert("end", s)
        prow = ttk.Frame(side, style="Panel.TFrame")
        prow.pack(fill="x")
        ttk.Button(prow, text=t("add"), command=lambda: self._add_folder(self.prot_list, "protected")).pack(side="left")
        ttk.Button(prow, text=t("remove"), command=lambda: self._remove_folder(self.prot_list, "protected")).pack(side="left", padx=4)

        ttk.Label(side, text=t("filetypes"), style="Section.TLabel").pack(anchor="w", pady=(12, 2))
        grid = ttk.Frame(side, style="Panel.TFrame")
        grid.pack(fill="x")
        sel = set(self.cfg["categories"])
        self.all_var = tk.BooleanVar(value=not sel)
        ttk.Checkbutton(grid, text=t("all_types"), variable=self.all_var,
                        command=self._cat_all_changed).grid(row=0, column=0, columnspan=2, sticky="w")
        self.cat_vars: dict[str, tk.BooleanVar] = {}
        for i, cat in enumerate(CATEGORY_ORDER):
            v = tk.BooleanVar(value=(not sel) or cat in sel)
            self.cat_vars[cat] = v
            ttk.Checkbutton(grid, text=t("cat_" + cat), variable=v, command=self._cat_changed).grid(
                row=1 + i // 2, column=i % 2, sticky="w", padx=(0, 8))

        ttk.Label(side, text=t("keep_rule"), style="Section.TLabel").pack(anchor="w", pady=(12, 2))
        self.rules = ["oldest", "newest", "shortest", "longest"]
        self.rule_cb = ttk.Combobox(side, state="readonly",
                                    values=[t("rule_" + r) for r in self.rules])
        self.rule_cb.current(self.rules.index(self.cfg["keep_rule"]) if self.cfg["keep_rule"] in self.rules else 0)
        self.rule_cb.pack(fill="x")

        ttk.Frame(side, style="Panel.TFrame", height=6).pack(fill="x")

    def _build_main(self, main: ttk.Frame) -> None:
        t, c = self.tr, self.c
        bar = ttk.Frame(main)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text=t("search")).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=28)
        self.search_entry.pack(side="left", padx=(4, 12))
        self.search_var.trace_add("write", lambda *_: self._schedule_refresh())
        ttk.Label(bar, text=t("filter_cat")).pack(side="left")
        self.fcat_keys = ["all"] + CATEGORY_ORDER
        self.fcat_cb = ttk.Combobox(bar, state="readonly", width=16,
                                    values=[t("cat_" + k) for k in self.fcat_keys])
        self.fcat_cb.current(0)
        self.fcat_cb.pack(side="left", padx=(4, 12))
        self.fcat_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_tree())
        ttk.Label(bar, text=t("sort")).pack(side="left")
        self.sort_keys = ["savings", "size", "count", "name"]
        self.sort_cb = ttk.Combobox(bar, state="readonly", width=18,
                                    values=[t("sort_" + k) for k in self.sort_keys])
        self.sort_cb.current(0)
        self.sort_cb.pack(side="left", padx=4)
        self.sort_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_tree())
        bar2 = ttk.Frame(main)
        bar2.pack(fill="x", pady=(0, 6))
        ttk.Label(bar2, text=t("view")).pack(side="left")
        self.view_keys = ["same", "folders", "similar"]
        self.view_cb = ttk.Combobox(bar2, state="readonly", width=26,
                                    values=[t("view_" + k) for k in self.view_keys])
        self.view_cb.current(self.view_keys.index(self.view) if self.view in self.view_keys else 0)
        self.view_cb.pack(side="left", padx=(4, 12))
        self.view_cb.bind("<<ComboboxSelected>>", lambda e: self._change_view())
        self.page_prev = ttk.Button(bar2, text="◀", width=3, command=lambda: self._goto_page(-1))
        self.page_prev.pack(side="left")
        self.page_var = tk.StringVar(value="")
        ttk.Label(bar2, textvariable=self.page_var).pack(side="left", padx=6)
        self.page_next = ttk.Button(bar2, text="▶", width=3, command=lambda: self._goto_page(1))
        self.page_next.pack(side="left")
        self.summary_var = tk.StringVar(value="")
        ttk.Label(bar2, textvariable=self.summary_var, foreground=c.accent).pack(side="right")

        paned = ttk.PanedWindow(main, orient="vertical")

        tree_frame = ttk.Frame(paned)
        cols = ("folder", "size", "date", "action")
        self.tree = ttk.Treeview(tree_frame, columns=cols, selectmode="extended")
        self.tree.heading("#0", text=t("col_name"))
        self.tree.heading("folder", text=t("col_folder"))
        self.tree.heading("size", text=t("col_size"))
        self.tree.heading("date", text=t("col_date"))
        self.tree.heading("action", text=t("col_action"))
        self.tree.column("#0", width=330, stretch=True)
        self.tree.column("folder", width=380, stretch=True)
        self.tree.column("size", width=90, anchor="e", stretch=False)
        self.tree.column("date", width=140, stretch=False)
        self.tree.column("action", width=120, stretch=False)
        self.tree.tag_configure("group", background=c.group_bg, foreground=c.accent, font=self.f_bold)
        self.tree.tag_configure("keep", foreground=c.green)
        self.tree.tag_configure("dup", foreground=c.fg)
        self.tree.tag_configure("archived", foreground=c.muted)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self.set_original())
        self.tree.bind("<space>", lambda e: (self.toggle_keep(), "break")[1])
        self.tree.bind("<Return>", lambda e: (self.set_original(), "break")[1])
        paned.add(tree_frame, weight=4)

        cmp_frame = ttk.Frame(paned, padding=(0, 8, 0, 0))
        self.cards = [self._build_card(cmp_frame, t("original"), c.green),
                      self._build_card(cmp_frame, t("duplicate"), c.yellow)]
        paned.add(cmp_frame, weight=2)

        acts = ttk.Frame(main, padding=(0, 8, 0, 0))
        self.btn_setorig = ttk.Button(acts, text=t("set_original"), command=self.set_original)
        self.btn_setorig.pack(side="left")
        self.btn_toggle = ttk.Button(acts, text=t("toggle"), command=self.toggle_keep)
        self.btn_toggle.pack(side="left", padx=4)
        self.btn_export = ttk.Button(acts, text=t("export"), command=self.export_report)
        self.btn_export.pack(side="right")
        self.btn_purge = ttk.Button(acts, text=t("purge"), style="Danger.TButton", command=self.show_purge)
        self.btn_purge.pack(side="right", padx=4)
        self.btn_undo = ttk.Button(acts, text=t("undo_last"), command=self.undo_last)
        self.btn_undo.pack(side="right")
        acts2 = ttk.Frame(main, padding=(0, 6, 0, 0))
        acts2.pack(side="bottom", fill="x")
        acts.pack(side="bottom", fill="x")
        paned.pack(fill="both", expand=True)
        self.btn_arch_sel = ttk.Button(acts2, text=t("archive_selected"), command=lambda: self.archive(False))
        self.btn_arch_sel.pack(side="left")
        self.btn_arch_all = ttk.Button(acts2, text=t("archive_all"), style="Accent.TButton",
                                       command=lambda: self.archive(True))
        self.btn_arch_all.pack(side="left", padx=6)

    def _build_card(self, parent: ttk.Frame, title: str, color: str) -> dict:
        c = self.c
        fr = tk.Frame(parent, bg=c.panel, highlightthickness=1, highlightbackground=c.border)
        fr.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(fr, text=title, bg=c.panel, fg=color, font=self.f_bold, anchor="w").pack(fill="x", padx=10, pady=(8, 4))
        inner = tk.Frame(fr, bg=c.panel)
        inner.pack(fill="both", expand=True, padx=10)
        canvas = tk.Canvas(inner, width=190, height=130, bg=c.field, highlightthickness=0)
        canvas.pack(side="left", anchor="n")
        info = tk.Label(inner, text="", bg=c.panel, fg=c.fg, font=self.f_small, justify="left",
                        anchor="nw", wraplength=380)
        info.pack(side="left", fill="both", expand=True, padx=(10, 0))
        btns = tk.Frame(fr, bg=c.panel)
        btns.pack(fill="x", padx=10, pady=8)
        card = {"frame": fr, "canvas": canvas, "info": info, "path": None}
        ttk.Button(btns, text=self.tr("open"),
                   command=lambda: card["path"] and open_with_default_app(card["path"])).pack(side="left")
        ttk.Button(btns, text=self.tr("reveal"),
                   command=lambda: card["path"] and reveal_in_file_manager(card["path"])).pack(side="left", padx=4)
        info.bind("<Configure>", lambda e: info.configure(wraplength=max(150, e.width - 10)))
        return card

    def _enable_drop(self, widget, target: str = "list") -> None:
        """Drag & Drop von Ordnern (F5) – nur wenn tkinterdnd2 vorhanden ist."""
        if not getattr(self.root, "_dz_dnd", False):
            return
        try:
            from tkinterdnd2 import DND_FILES  # type: ignore

            def drop(event):
                for p in self.root.tk.splitlist(event.data):
                    p = os.path.normpath(p)
                    if not os.path.isdir(p):
                        continue
                    if target == "entry":
                        self.archive_var.set(p)
                    elif p not in widget.get(0, "end"):
                        widget.insert("end", p)
                self._sync_cfg()
                return event.action
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", drop)
        except Exception:
            log.debug("Drag & Drop nicht verfuegbar", exc_info=True)

    def _bind_keys(self) -> None:
        r = self.root
        r.bind("<F5>", lambda e: self.start_scan())
        r.bind("<F1>", lambda e: self.show_info())
        r.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        r.bind("<Control-z>", lambda e: self.undo_last())
        r.bind("<Escape>", lambda e: self.cancel_work() if self.busy_kind else None)

    # ================================================================ Ordnerverwaltung
    def _add_folder(self, lb: tk.Listbox, key: str) -> None:
        d = filedialog.askdirectory(parent=self.root, mustexist=True)
        if not d:
            return
        d = os.path.normpath(d)
        if d not in lb.get(0, "end"):
            lb.insert("end", d)
        self._sync_cfg()

    def _remove_folder(self, lb: tk.Listbox, key: str) -> None:
        for i in reversed(lb.curselection()):
            lb.delete(i)
        self._sync_cfg()

    def _move_src(self, delta: int) -> None:
        sel = self.src_list.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= self.src_list.size():
            return
        val = self.src_list.get(i)
        self.src_list.delete(i)
        self.src_list.insert(j, val)
        self.src_list.selection_set(j)
        self._sync_cfg()

    def _choose_archive(self) -> None:
        d = filedialog.askdirectory(parent=self.root)
        if d:
            self.archive_var.set(os.path.normpath(d))
            self._sync_cfg()

    def _cat_all_changed(self) -> None:
        for v in self.cat_vars.values():
            v.set(bool(self.all_var.get()))

    def _cat_changed(self) -> None:
        self.all_var.set(all(v.get() for v in self.cat_vars.values()))

    def _sync_cfg(self) -> None:
        self.cfg["sources"] = list(self.src_list.get(0, "end"))
        self.cfg["protected"] = list(self.prot_list.get(0, "end"))
        self.cfg["archive"] = self.archive_var.get().strip()
        cats = [k for k, v in self.cat_vars.items() if v.get()]
        self.cfg["categories"] = [] if len(cats) == len(self.cat_vars) else cats
        try:
            self.cfg["keep_rule"] = self.rules[self.rule_cb.current()]
        except (IndexError, tk.TclError):
            pass
        config.save(self.data_dir, self.cfg)

    def _options(self) -> ScanOptions:
        self._sync_cfg()
        cf = self.cfg
        return ScanOptions(
            sources=cf["sources"], archive=cf["archive"], protected=cf["protected"],
            excludes=cf["excludes"], categories=cf["categories"], min_size=int(cf["min_size"]),
            include_hidden=cf["include_hidden"], skip_cloud_only=cf["skip_cloud_only"],
            protect_catalogs=cf["protect_catalogs"], prefer_source_order=cf["prefer_source_order"],
            keep_rule=cf["keep_rule"], workers=int(cf["workers"]), verify_bytes=cf["verify_bytes"],
            move_sidecars=cf["move_sidecars"], prefer=list(cf.get("prefer", [])),
            avoid=list(cf.get("avoid", [])), find_folders=bool(cf.get("find_folders", True)),
            find_similar=bool(cf.get("find_similar", False)),
            remove_empty_dirs=bool(cf.get("remove_empty_dirs", True)))

    # ================================================================ Hintergrundarbeit
    def _set_busy(self, kind: str | None) -> None:
        self.busy_kind = kind
        idle = kind is None
        st_idle = "!disabled" if idle else "disabled"
        st_busy = "disabled" if idle else "!disabled"
        for b in (self.scan_btn, self.btn_arch_sel, self.btn_arch_all, self.btn_undo, self.btn_purge,
                  self.btn_setorig, self.btn_toggle, self.btn_export):
            try:
                b.state([st_idle])
            except tk.TclError:
                pass
        for b in (self.pause_btn, self.cancel_btn):
            try:
                b.state([st_busy])
            except tk.TclError:
                pass
        if idle:
            self.pause_btn.configure(text=self.tr("pause"))

    def _start(self, kind: str, target, *args) -> bool:
        if self.busy_kind:
            self.info(self.tr("busy"))
            return False
        self.control = Control()
        self._set_busy(kind)
        self.progress.configure(mode="determinate", value=0)

        def runner() -> None:
            try:
                with KeepAwake():  # ST1: kein Standby waehrend des Laufs
                    result = target(*args)
                self.q.put(("done", kind, result))
            except Cancelled:
                self.q.put(("cancelled", kind, None))
            except NeedsAttention as exc:
                log.warning("Lauf angehalten: %s", exc)
                self.q.put(("attention", kind, str(exc)))
            except Exception as exc:
                log.error("Fehler (%s): %s\n%s", kind, exc, traceback.format_exc())
                self.q.put(("error", kind, f"{type(exc).__name__}: {exc}"))
        self.worker = threading.Thread(target=runner, name=f"dz-{kind}", daemon=True)
        self.worker.start()
        return True

    def _progress_cb(self, d: dict) -> None:
        self.q.put(("progress", d))

    def toggle_pause(self) -> None:
        if not self.control:
            return
        if self.control.paused:
            self.control.resume()
            self.pause_btn.configure(text=self.tr("pause"))
        else:
            self.control.pause()
            self.pause_btn.configure(text=self.tr("resume"))

    def cancel_work(self) -> None:
        if self.control:
            self.control.cancel()

    def poll(self) -> None:
        try:
            progress = None
            for _ in range(500):
                try:
                    msg = self.q.get_nowait()
                except queue.Empty:
                    break
                kind = msg[0]
                if kind == "progress":
                    progress = msg[1]
                elif kind == "log":
                    self._append_log(msg[1])
                elif kind == "done":
                    self._on_done(msg[1], msg[2])
                elif kind == "cancelled":
                    self._finish(self.tr("cancelled"))
                    self._reload_groups()
                elif kind == "error":
                    self._finish("⚠ " + msg[2])
                    self.info(self.tr("crash", err=msg[2]), "error")
                elif kind == "attention":
                    self._finish("⚠ " + msg[2])
                    self._reload_groups()
                    self.info(self.tr("attention", msg=msg[2]), "warning")
                elif kind == "preview":
                    self._show_preview(msg[1], msg[2], msg[3])
            if progress:
                self._show_progress(progress)
        finally:
            self.root.after(100, self.poll)

    def _show_progress(self, d: dict) -> None:
        t = self.tr
        ph = d.get("phase", "")
        if ph == "enumerate":
            if str(self.progress.cget("mode")) != "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress.start(15)
            self.status_var.set(t("ph_enumerate", files=d.get("files", 0), dirs=d.get("dirs", 0)))
            self.rate_var.set(_short(d.get("current", ""), 60))
            return
        if ph in ("waiting", "folders"):
            if str(self.progress.cget("mode")) != "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress.start(15)
            self.status_var.set(t("ph_waiting", root=d.get("current", "")) if ph == "waiting" else t("ph_folders"))
            self.rate_var.set("")
            return
        if str(self.progress.cget("mode")) == "indeterminate":
            self.progress.stop()
            self.progress.configure(mode="determinate")
        tb = d.get("total_bytes") or 0
        tot = d.get("total") or 0
        if tb and ph in ("partial", "full"):
            val = min(100.0, 100.0 * d.get("bytes", 0) / tb)
        elif tot:
            val = 100.0 * d.get("files", 0) / tot
        else:
            val = 0
        self.progress.configure(value=val)
        key = {"partial": "ph_partial", "full": "ph_full", "archive": "ph_archive",
               "undo": "ph_undo", "purge": "ph_purge", "similar": "ph_similar",
               "recover": "ph_archive"}.get(ph, "ph_full")
        text = t(key, files=d.get("files", 0), total=tot)
        if d.get("cached"):
            text += "  ·  " + t("cached", n=d["cached"])
        self.status_var.set(text)
        rate = d.get("rate") or 0
        parts = []
        if rate > 0:
            parts.append(f"{human_size(rate, self.cfg['lang'])}/s")
        if d.get("eta"):
            parts.append("≈ " + human_duration(d["eta"]))
        self.rate_var.set("   ".join(parts))

    def _finish(self, text: str) -> None:
        try:
            self.progress.stop()
        except tk.TclError:
            pass
        self.progress.configure(mode="determinate", value=100)
        self.status_var.set(text)
        self.rate_var.set("")
        self._set_busy(None)
        if self.cfg.get("tts"):
            speak(text)

    def _on_done(self, kind: str, result) -> None:
        t, lang = self.tr, self.cfg["lang"]
        if kind == "scan":
            scanner, sid, groups = result
            self.session_id, self.groups = sid, groups
            self.folder_groups = scanner.folder_groups
            self.session_stats = scanner.stats
            st = scanner.stats
            msg = t("scan_done", files=st["files"], groups=st["groups"], dups=st["duplicates"],
                    size=human_size(st["wasted"], lang), sec=st["seconds"]) if groups else t("no_dupes")
            if st["errors"]:
                msg += "  " + t("errors_during", n=st["errors"])
            self._index_groups()
            self._refresh_tree()
            self._finish(msg)
        elif kind in ("archive", "undo"):
            key = "archive_done" if kind == "archive" else "undo_done"
            if self.session_id is None and kind == "undo":
                self._finish(t(key, **result))
                return
            self._reload_groups()
            self._finish(t(key, **result))
        elif kind == "purge":
            self._finish(t("purge_done", purged=result["purged"], kept=result["kept"],
                           failed=result["failed"], size=human_size(result["bytes"], lang)))
        elif kind == "recover":
            self._reload_groups()
            self._finish(t("archive_done", **result))

    # ================================================================ Scan
    def start_scan(self) -> None:
        if self.busy_kind:
            return
        opts = self._options()
        errs = validate_options(opts)
        if errs:
            self.info("\n".join(self.tr.error(e) for e in errs), "warning")
            return
        lines = []
        for src in opts.sources:  # S7: Laufwerkswurzel / System- / Benutzerordner
            r = risky_source(src)
            if r:
                lines.append("• " + self.tr("warn_" + r, x=src))
        if lines and not self.ask_yes_no(APP_NAME, self.tr("warn_sources", lines="\n".join(lines))):
            return
        self._scan(opts, None)

    def _scan(self, opts: ScanOptions, session_id: int | None) -> None:
        def job():
            sc = Scanner(self.store, self.control, self._progress_cb)  # type: ignore[arg-type]
            sid, groups = sc.run(opts, session_id)
            return sc, sid, groups
        self.groups = []
        self._index_groups()
        self._refresh_tree()
        self._start("scan", job)

    # ================================================================ Ergebnisliste
    def _index_groups(self) -> None:
        self.group_by_id = {g["gid"]: g for g in self.groups}

    def _reload_groups(self) -> None:
        if self.session_id is None:
            return
        self.groups = self.store.dupes_load(self.session_id)
        self.folder_groups = self.store.folders_load(self.session_id)
        self._index_groups()
        self._refresh_tree()

    def _schedule_refresh(self) -> None:
        if getattr(self, "_refresh_job", None):
            try:
                self.root.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
        self.page = 0
        self._refresh_job = self.root.after(300, self._refresh_tree)

    def _change_view(self) -> None:
        try:
            self.view = self.view_keys[self.view_cb.current()]
        except (IndexError, tk.TclError):
            self.view = "same"
        self.page = 0
        self._refresh_tree()

    def _goto_page(self, delta: int) -> None:
        self.page = max(0, self.page + delta)
        self._refresh_tree()

    def _kind_groups(self) -> list[dict]:
        kind = "similar" if self.view == "similar" else "same"
        return [g for g in self.groups if g.get("kind", "same") == kind]

    def _visible_groups(self) -> list[dict]:
        q = (self.search_var.get() if hasattr(self, "search_var") else "").strip().lower()
        try:
            fcat = self.fcat_keys[self.fcat_cb.current()]
        except (AttributeError, IndexError, tk.TclError):
            fcat = "all"
        out = []
        for g in self._kind_groups():
            if fcat != "all" and category_of(g["members"][0]["path"]) != fcat:
                continue
            if q and not any(q in m["path"].lower() for m in g["members"]):
                continue
            out.append(g)
        try:
            sk = self.sort_keys[self.sort_cb.current()]
        except (AttributeError, IndexError, tk.TclError):
            sk = "savings"
        if sk == "size":
            out.sort(key=lambda g: -g["size"])
        elif sk == "count":
            out.sort(key=lambda g: -len(g["members"]))
        elif sk == "name":
            out.sort(key=lambda g: os.path.basename(g["members"][0]["path"]).lower())
        else:
            out.sort(key=lambda g: -(g["size"] * max(0, len(g["members"]) - 1)))
        return out

    def _visible_folders(self) -> list[dict]:
        q = (self.search_var.get() if hasattr(self, "search_var") else "").strip().lower()
        out = [fg for fg in self.folder_groups
               if not q or any(q in f["path"].lower() for f in fg["folders"])]
        try:
            sk = self.sort_keys[self.sort_cb.current()]
        except (AttributeError, IndexError, tk.TclError):
            sk = "savings"
        if sk == "count":
            out.sort(key=lambda fg: -len(fg["folders"]))
        elif sk == "name":
            out.sort(key=lambda fg: os.path.basename(fg["folders"][0]["path"]).lower())
        else:
            out.sort(key=lambda fg: -fg["size"] * max(1, len(fg["folders"]) - 1))
        return out

    def _group_text(self, g: dict) -> str:
        lang = self.cfg["lang"]
        n_dup = sum(1 for m in g["members"] if not m.get("keep") and m.get("state") != "archived")
        txt = self.tr("group_line", gid=g["gid"], n=len(g["members"]), size=human_size(g["size"], lang),
                      save=human_size(g["size"] * n_dup, lang),
                      cat=self.tr("cat_" + category_of(g["members"][0]["path"])))
        if g.get("kind") == "similar":
            txt += " · " + self.tr("similar_tag")
        return txt

    def _refresh_tree(self) -> None:
        self._refresh_job = None
        if not hasattr(self, "tree"):
            return
        self.tree.delete(*self.tree.get_children())
        self.iid_member.clear()
        self.iid_folder.clear()
        self.populated.clear()
        lang = self.cfg["lang"]
        if self.view == "folders":
            vis = self._visible_folders()
        else:
            vis = self._visible_groups()
        pages = max(1, (len(vis) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = min(self.page, pages - 1)
        shown = vis[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        if self.view == "folders":
            for i, fg in enumerate(shown):
                self._insert_folder_group(fg, i < 40)
        else:
            for i, g in enumerate(shown):
                gi = f"g{g['gid']}"
                self.tree.insert("", "end", iid=gi, text=self._group_text(g), tags=("group",), open=False)
                if i < 40:
                    self._populate(g["gid"])
                    self.tree.item(gi, open=True)
                else:
                    self.tree.insert(gi, "end", iid=f"{gi}:dummy", text="…")
        try:
            self.page_var.set(self.tr("page", p=self.page + 1, n=pages) if len(vis) > PAGE_SIZE else "")
            self.page_prev.state(["!disabled"] if self.page > 0 else ["disabled"])
            self.page_next.state(["!disabled"] if self.page < pages - 1 else ["disabled"])
        except (AttributeError, tk.TclError):
            pass
        same = [g for g in self.groups if g.get("kind", "same") == "same"]
        dups = sum(1 for g in same for m in g["members"] if not m.get("keep") and m.get("state") != "archived")
        wasted = sum(g["size"] for g in same for m in g["members"] if not m.get("keep") and m.get("state") != "archived")
        summ = f"{len(same)} · {dups} ⇢ · {human_size(wasted, lang)}" if same else ""
        self.summary_var.set(summ)
        for card in getattr(self, "cards", []):
            self._fill_card(card, None, None)

    def _insert_folder_group(self, fg: dict, open_: bool) -> None:
        lang = self.cfg["lang"]
        fi = f"f{fg['fgid']}"
        n_arch = sum(1 for f in fg["folders"] if not f.get("keep"))
        self.tree.insert("", "end", iid=fi, open=open_, tags=("group",), text=self.tr(
            "folder_line", fgid=fg["fgid"], n=len(fg["folders"]), files=fg["files"],
            size=human_size(fg["size"], lang), save=human_size(fg["size"] * n_arch, lang)))
        for idx, f in enumerate(fg["folders"]):
            iid = f"{fi}:{idx}"
            self.iid_folder[iid] = (fg["fgid"], idx)
            self.tree.insert(fi, "end", iid=iid, text=os.path.basename(f["path"].rstrip("\\/")) or f["path"],
                             values=(os.path.dirname(f["path"]), human_size(f["size"], lang), "",
                                     self.tr("act_keep_folder") if f.get("keep") else self.tr("act_archive_folder")),
                             tags=("keep" if f.get("keep") else "dup",))

    def _populate(self, gid: int) -> None:
        if gid in self.populated:
            return
        g = self.group_by_id.get(gid)
        if not g:
            return
        gi = f"g{gid}"
        dummy = f"{gi}:dummy"
        if self.tree.exists(dummy):
            self.tree.delete(dummy)
        lang = self.cfg["lang"]
        for idx, m in enumerate(g["members"]):
            iid = f"{gi}:{idx}"
            self.iid_member[iid] = (gid, idx)
            self.tree.insert(gi, "end", iid=iid, text=os.path.basename(m["path"]),
                             values=(os.path.dirname(m["path"]), human_size(m.get("size", g["size"]), lang),
                                     human_time(m["mtime_ns"], lang), self._action_text(m)),
                             tags=(self._member_tag(m),))
        self.populated.add(gid)

    def _action_text(self, m: dict) -> str:
        if m.get("state") == "archived":
            return self.tr("act_archived")
        return self.tr("act_keep") if m.get("keep") else self.tr("act_archive")

    @staticmethod
    def _member_tag(m: dict) -> str:
        if m.get("state") == "archived":
            return "archived"
        return "keep" if m.get("keep") else "dup"

    def _on_open(self, _e=None) -> None:
        iid = self.tree.focus()
        if iid.startswith("g") and ":" not in iid:
            self._populate(int(iid[1:]))

    def _selected_member(self) -> tuple[dict, dict] | None:
        iid = self.tree.focus()
        if iid in self.iid_member:
            gid, idx = self.iid_member[iid]
            g = self.group_by_id[gid]
            return g, g["members"][idx]
        return None

    def _folder_by_iid(self, iid: str) -> tuple[dict, dict] | None:
        if iid in self.iid_folder:
            fgid, idx = self.iid_folder[iid]
            fg = next((x for x in self.folder_groups if x["fgid"] == fgid), None)
            if fg:
                return fg, fg["folders"][idx]
        return None

    def _on_select(self, _e=None) -> None:
        iid = self.tree.focus()
        if self.view == "folders":
            sel = self._folder_by_iid(iid)
            fg = sel[0] if sel else (next((x for x in self.folder_groups if f"f{x['fgid']}" == iid), None))
            if not fg:
                return
            keep = next((f for f in fg["folders"] if f.get("keep")), fg["folders"][0])
            other = sel[1] if sel and sel[1] is not keep else next((f for f in fg["folders"] if f is not keep), None)
            self._fill_folder_card(self.cards[0], keep, fg)
            self._fill_folder_card(self.cards[1], other, fg)
            return
        g = None
        sel_m = None
        if iid in self.iid_member:
            gid, idx = self.iid_member[iid]
            g = self.group_by_id.get(gid)
            sel_m = g["members"][idx] if g else None
        elif iid.startswith("g") and ":" not in iid:
            g = self.group_by_id.get(int(iid[1:]))
        if not g:
            return
        keeper = next((m for m in g["members"] if m.get("keep")), g["members"][0])
        other = sel_m if sel_m is not None and sel_m is not keeper else next(
            (m for m in g["members"] if m is not keeper), None)
        self._fill_card(self.cards[0], keeper, g)
        self._fill_card(self.cards[1], other, g)

    def _fill_folder_card(self, card: dict, f: dict | None, fg: dict) -> None:
        cv: tk.Canvas = card["canvas"]
        cv.delete("all")
        card["path"] = f["path"] if f else None
        if not f:
            card["info"].configure(text="")
            return
        lang, t, c = self.cfg["lang"], self.tr, self.c
        card["info"].configure(text=(
            f"{os.path.basename(f['path'].rstrip(os.sep)) or f['path']}\n\n{t('path')}: {f['path']}\n"
            f"{t('col_size')}: {human_size(f['size'], lang)} · {f['files']} {t('br_files').split()[0]}\n"
            f"{t('col_action')}: {t('act_keep_folder') if f.get('keep') else t('act_archive_folder')}"))
        w, h = int(cv.cget("width")), int(cv.cget("height"))
        cv.create_rectangle(w // 2 - 50, h // 2 - 30, w // 2 + 50, h // 2 + 40, outline=c.accent, width=2)
        cv.create_rectangle(w // 2 - 50, h // 2 - 42, w // 2 - 10, h // 2 - 30, outline=c.accent, width=2)
        cv.create_text(w // 2, h // 2 + 5, text=str(f["files"]), fill=c.fg, font=self.f_bold)

    def _fill_card(self, card: dict, m: dict | None, g: dict | None) -> None:
        cv: tk.Canvas = card["canvas"]
        cv.delete("all")
        card["path"] = m["path"] if m else None
        if not m or not g:
            card["info"].configure(text="")
            return
        lang = self.cfg["lang"]
        t = self.tr
        path = m["path"]
        created = "?"
        try:
            st = os.stat(fs(path))
            ctime = getattr(st, "st_birthtime", None) or (st.st_ctime if IS_WIN else None)
            if ctime:
                created = human_time(ctime, lang)
        except OSError:
            pass
        state = t("act_archived") if m.get("state") == "archived" else (
            t("act_keep") if m.get("keep") else t("act_archive"))
        size = m.get("size", g["size"])
        card["info"].configure(text=(
            f"{os.path.basename(path)}\n\n{t('path')}: {os.path.dirname(path)}\n"
            f"{t('col_size')}: {human_size(size, lang)} ({_thousands(size, lang)} B)\n"
            f"{t('col_date')}: {human_time(m['mtime_ns'], lang)}\n{t('created')}: {created}\n"
            f"{t('type')}: {t('cat_' + category_of(path))} (.{ext_of(path) or '–'})\n"
            f"{t('hash')}: {g['hash'][:32]}…\n{t('col_action')}: {state}"))
        self._draw_placeholder(cv, path)
        self._request_preview(card, path)

    def _draw_placeholder(self, cv: tk.Canvas, path: str) -> None:
        c = self.c
        w, h = int(cv.cget("width")), int(cv.cget("height"))
        ext = ext_of(path)
        cv.create_rectangle(w // 2 - 34, h // 2 - 46, w // 2 + 34, h // 2 + 36, outline=c.accent, width=2)
        cv.create_text(w // 2, h // 2 - 5, text=("." + ext.upper()) if ext else "?", fill=c.fg, font=self.f_bold)
        cv.create_text(w // 2, h // 2 + 52, text=self.tr("cat_" + category_of(path)), fill=c.muted,
                       font=self.f_small)

    def _request_preview(self, card: dict, path: str) -> None:
        """Vorschau im Hintergrund erzeugen (ST3) – die Oberflaeche blockiert nie."""
        self._preview_token += 1
        token = self._preview_token
        card["token"] = token
        cv = card["canvas"]
        box = (int(cv.cget("width")), int(cv.cget("height")))

        if getattr(self, "_pv_q", None) is None:
            self._pv_q = queue.Queue()
            threading.Thread(target=self._preview_worker, name="dz-preview", daemon=True).start()
        self._pv_q.put((card, token, path, box))

    def _preview_worker(self) -> None:
        """Ein einziger Vorschau-Thread; veraltete Anfragen werden verworfen."""
        while True:
            req = self._pv_q.get()
            latest = {id(req[0]): req}
            try:
                while True:
                    r = self._pv_q.get_nowait()
                    latest[id(r[0])] = r
            except queue.Empty:
                pass
            for card, token, path, box in latest.values():
                if card.get("token") != token:
                    continue
                try:
                    img = make_preview(path, box)
                except Exception:
                    img = None
                if img is not None:
                    self.q.put(("preview", card, token, img))

    def _show_preview(self, card: dict, token: int, img) -> None:
        if card.get("token") != token or ImageTk is None:
            return
        try:
            photo = ImageTk.PhotoImage(img)
            cv = card["canvas"]
            cv.delete("all")
            w, h = int(cv.cget("width")), int(cv.cget("height"))
            cv.create_image(w // 2, h // 2, image=photo)
            self._img_refs = (self._img_refs + [photo])[-6:]
        except (tk.TclError, ValueError, TypeError):
            pass

    def _update_group_rows(self, g: dict) -> None:
        gi = f"g{g['gid']}"
        if self.tree.exists(gi):
            self.tree.item(gi, text=self._group_text(g))
        for idx, m in enumerate(g["members"]):
            iid = f"{gi}:{idx}"
            if self.tree.exists(iid):
                vals = list(self.tree.item(iid, "values"))
                if len(vals) == 4:
                    vals[3] = self._action_text(m)
                self.tree.item(iid, values=vals, tags=(self._member_tag(m),))
        self._on_select()

    def toggle_keep(self) -> None:
        if self.busy_kind or self.view == "folders":
            return
        sm = self._selected_member()
        if not sm:
            return
        g, m = sm
        if m.get("state") == "archived":
            return
        if m.get("keep") and sum(1 for x in g["members"] if x.get("keep")) <= 1:
            self.info(self.tr("need_keeper"))
            return
        m["keep"] = not m.get("keep")
        if self.session_id is not None:
            self.store.dupes_set_keep(self.session_id, m["path"], m["keep"], g["gid"])
        self._update_group_rows(g)

    def set_original(self) -> None:
        if self.busy_kind:
            return
        if self.view == "folders":
            self._set_original_folder()
            return
        sm = self._selected_member()
        if not sm:
            return
        g, m = sm
        if m.get("state") == "archived":
            return
        for x in g["members"]:
            if x.get("state") == "archived":
                continue
            x["keep"] = x is m
            if self.session_id is not None:
                self.store.dupes_set_keep(self.session_id, x["path"], x["keep"], g["gid"])
        self._update_group_rows(g)

    def _set_original_folder(self) -> None:
        sel = self._folder_by_iid(self.tree.focus())
        if not sel:
            return
        fg, f = sel
        for x in fg["folders"]:
            x["keep"] = x is f
        self.store.folders_store(self.session_id, self.folder_groups) if self.session_id else None
        self._apply_folder_choice(fg)
        self._refresh_tree()

    def _apply_folder_choice(self, fg: dict) -> list[dict]:
        """Uebertraegt die Ordner-Wahl auf die Dateigruppen: Dateien im Original-
        Ordner werden behalten, die gleichen Dateien in den anderen Ordnern
        archiviert. Rueckgabe: betroffene Dateigruppen."""
        keep_dirs = [f["path"] for f in fg["folders"] if f.get("keep")]
        arch_dirs = [f["path"] for f in fg["folders"] if not f.get("keep")]
        touched = []
        for g in self.groups:
            if g.get("kind", "same") != "same":
                continue
            inside_keep = [m for m in g["members"] if any(is_within(m["path"], d) for d in keep_dirs)]
            inside_arch = [m for m in g["members"] if any(is_within(m["path"], d) for d in arch_dirs)]
            if not inside_keep or not inside_arch:
                continue
            for m in inside_arch:
                if m.get("state") != "archived":
                    m["keep"] = False
            if not any(m.get("keep") for m in g["members"]):
                inside_keep[0]["keep"] = True
            for m in g["members"]:
                if self.session_id is not None:
                    self.store.dupes_set_keep(self.session_id, m["path"], bool(m.get("keep")), g["gid"])
            # nur die Dateien dieser Ordner – andere Kopien der Gruppe bleiben unberuehrt
            sub = dict(g)
            sub["members"] = [m for m in g["members"]
                              if m in inside_keep or m in inside_arch or m.get("keep")]
            if not any(m.get("keep") for m in sub["members"]):
                continue
            touched.append(sub)
        return touched

    # ================================================================ Archivieren
    def archive(self, all_groups: bool) -> None:
        if self.busy_kind or not self.groups or self.session_id is None:
            if not self.groups:
                self.info(self.tr("nothing_selected"))
            return
        self._sync_cfg()
        if self.view == "folders":
            fgs = self._visible_folders() if all_groups else [
                fg for fg in self.folder_groups
                if f"f{fg['fgid']}" in self.tree.selection()
                or any(self.iid_folder.get(i, (None,))[0] == fg["fgid"] for i in self.tree.selection())]
            groups = [g for fg in fgs for g in self._apply_folder_choice(fg)]
        elif all_groups:
            groups = self._visible_groups()
        else:
            gids: set[int] = set()
            for iid in self.tree.selection():
                if iid in self.iid_member:
                    gids.add(self.iid_member[iid][0])
                elif iid.startswith("g") and ":" not in iid:
                    gids.add(int(iid[1:]))
            groups = [self.group_by_id[x] for x in sorted(gids) if x in self.group_by_id]
        groups = [g for g in groups if any(m.get("keep") for m in g["members"])]
        movers = [(g, m) for g in groups for m in g["members"] if not m.get("keep") and m.get("state", "open") == "open"]
        n = len(movers)
        size = sum(m.get("size", g["size"]) for g, m in movers)
        if n == 0:
            self.info(self.tr("nothing_selected"))
            return
        archive = self.cfg["archive"]
        errs = [e for e in validate_options(self._options()) if e.startswith(("err_no_archive", "err_source_in"))]
        if errs:
            self.info("\n".join(self.tr.error(e) for e in errs), "warning")
            return
        kind = cloud_sync_kind(archive)
        if kind and not self.ask_yes_no(self.tr("confirm_archive_title"), self.tr("warn_cloud", kind=kind)):
            return
        n_sim = sum(1 for g, m in movers if g.get("kind") == "similar")
        if n_sim and not self.ask_yes_no(self.tr("confirm_archive_title"), self.tr("confirm_similar", n=n_sim)):
            return
        if not self.ask_yes_no(self.tr("confirm_archive_title"),
                               self.tr("confirm_archive", n=n, size=human_size(size, self.cfg["lang"]),
                                       archive=archive)):
            return
        sid = self.session_id
        verify = bool(self.cfg["verify_bytes"])
        sidecars = bool(self.cfg["move_sidecars"])
        roots = list(self.cfg["sources"]) if self.cfg.get("remove_empty_dirs") else []

        def job():
            arch = Archiver(self.store, self.control, self._progress_cb, verify_bytes=verify)  # type: ignore[arg-type]
            arch.empty_dir_roots = roots
            rid = arch.plan_archive(sid, groups, archive, sidecars)
            return arch.execute(rid)
        self._start("archive", job)

    def _new_control(self) -> Control:
        return Control()

    def _run_undo(self, run: dict, entry_ids: list[int] | None) -> None:
        if run.get("session_id"):
            self.session_id = run["session_id"]

        def job():
            arch = Archiver(self.store, self.control, self._progress_cb)  # type: ignore[arg-type]
            return arch.execute(arch.plan_undo(run["id"], entry_ids))
        self._start("undo", job)

    def _resume_run(self, run: dict) -> None:
        self.session_id = run.get("session_id") or self.session_id
        roots = list(self.cfg["sources"]) if self.cfg.get("remove_empty_dirs") else []

        def job():
            arch = Archiver(self.store, self.control, self._progress_cb,  # type: ignore[arg-type]
                            verify_bytes=bool(self.cfg["verify_bytes"]))
            arch.empty_dir_roots = roots
            return arch.execute(run["id"])
        if self.session_id:
            self._reload_groups()
        self._start("recover", job)

    def _last_archive_run(self) -> dict | None:
        for r in self.store.runs_list("archive"):
            if r["state"] in ("done", "cancelled") and self.store.journal_entries(r["id"], (J_DONE,)):
                return r
        return None

    def undo_last(self) -> None:
        if self.busy_kind:
            return
        run = self._last_archive_run()
        if not run:
            self.info(self.tr("no_runs"))
            return
        if not self.ask_yes_no(APP_NAME, self.tr("undo_confirm", id=run["id"])):
            return
        self._run_undo(run, None)

    # ================================================================ Bereinigen (Freigabe)
    def show_purge(self) -> None:
        if self.busy_kind:
            return
        runs = [r for r in self.store.runs_list("archive", 200)
                if self.store.journal_entries(r["id"], (J_DONE,))]
        if not runs:
            self.info(self.tr("no_runs"))
            return
        t, c = self.tr, self.c
        win = self._dialog(t("purge_title"), "760x520")
        ttk.Label(win, text=t("purge_intro"), style="Panel.TLabel", justify="left").pack(anchor="w", padx=14, pady=(14, 8))
        tv = ttk.Treeview(win, columns=("date", "files", "size", "archive"), show="headings", height=8,
                          selectmode="extended")
        for col, txt, wd in (("date", t("col_date"), 140), ("files", "#", 60), ("size", t("col_size"), 90),
                             ("archive", t("archive"), 400)):
            tv.heading(col, text=txt)
            tv.column(col, width=wd)
        network = False
        for r in runs:
            ent = self.store.journal_entries(r["id"], (J_DONE,))
            tv.insert("", "end", iid=str(r["id"]), values=(
                human_time(r["created"], self.cfg["lang"]), len(ent),
                human_size(sum(e["size"] or 0 for e in ent), self.cfg["lang"]), r["archive"]))
            network = network or is_network_path(r["archive"])
        mode = tk.StringVar(value="perm" if network else "trash")
        f = ttk.Frame(win, style="Panel.TFrame", padding=14)
        rb = ttk.Radiobutton(f, text=t("purge_trash"), value="trash", variable=mode)
        rb.pack(anchor="w")
        if network:
            rb.state(["disabled"])
        ttk.Radiobutton(f, text=t("purge_perm"), value="perm", variable=mode).pack(anchor="w")
        if network:
            ttk.Label(f, text=t("purge_network"), style="Panel.TLabel", foreground=c.yellow,
                      wraplength=700).pack(anchor="w", pady=(6, 0))
        ttk.Label(f, text=t("purge_confirm"), style="Panel.TLabel").pack(anchor="w", pady=(10, 2))
        word = tk.StringVar()
        ttk.Entry(f, textvariable=word, width=20).pack(anchor="w")
        btns = ttk.Frame(win, style="Panel.TFrame", padding=(14, 0, 14, 14))
        btns.pack(side="bottom", fill="x")
        f.pack(side="bottom", fill="x")
        tv.pack(fill="both", expand=True, padx=14)
        go = ttk.Button(btns, text=t("purge_go"), style="Accent.TButton")
        go.pack(side="right")
        ttk.Button(btns, text=t("close"), command=win.destroy).pack(side="right", padx=6)
        go.state(["disabled"])

        def check(*_):
            ok = word.get().strip().upper() == t("purge_word") and bool(tv.selection())
            go.state(["!disabled"] if ok else ["disabled"])
        word.trace_add("write", check)
        tv.bind("<<TreeviewSelect>>", check)

        def run():
            ids = [int(x) for x in tv.selection()]
            trash = mode.get() == "trash"
            win.destroy()

            def job():
                return Archiver(self.store, self.control).purge(ids, use_trash=trash)  # type: ignore[arg-type]
            self.status_var.set(self.tr("ph_purge"))
            self._start("purge", job)
        go.configure(command=run)

    # ================================================================ Bericht
    def export_report(self) -> None:
        if not self.groups:
            self.info(self.tr("no_dupes"))
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".html",
            initialfile=f"DateiZwilling-Bericht-{time.strftime('%Y%m%d-%H%M')}.html",
            filetypes=[("HTML", "*.html"), ("CSV", "*.csv")])
        if not path:
            return
        try:
            anon = bool(self.cfg.get("anonymize"))
            if path.lower().endswith(".csv"):
                write_csv(path, self.groups, anonymize=anon)
            else:
                write_html(path, self.groups, self.session_stats, self.cfg["lang"], anonymize=anon)
            open_with_default_app(path)
        except OSError as exc:
            self.info(str(exc), "error")

    # ================================================================ Dialoge
    def info(self, text: str, kind: str = "info", parent: tk.Misc | None = None) -> None:
        dark_dialog(parent or self.root, self.c, self.f_normal, self.f_bold, APP_NAME, text, kind,
                    (("ok", self.tr("ok")),), "ok", "ok")

    def ask_yes_no(self, title: str, text: str) -> bool:
        return dark_dialog(self.root, self.c, self.f_normal, self.f_bold, title, text, "question",
                           (("yes", self.tr("yes")), ("no", self.tr("no"))), "yes", "no") == "yes"

    def ask_yes_no_cancel(self, title: str, text: str):
        v = dark_dialog(self.root, self.c, self.f_normal, self.f_bold, title, text, "question",
                        (("yes", self.tr("yes")), ("no", self.tr("no")), ("cancel", self.tr("btn_cancel"))),
                        "yes", "cancel")
        return {"yes": True, "no": False}.get(v)

    def _dialog(self, title: str, geometry: str | None) -> tk.Toplevel:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=self.c.panel)
        if geometry:
            try:  # nicht groesser als der Bildschirm
                gw, gh = (int(v) for v in geometry.split("x"))
                gw = min(gw, int(self.root.winfo_screenwidth() * 0.95))
                gh = min(gh, int(self.root.winfo_screenheight() * 0.88))
                geometry = f"{gw}x{gh}"
            except (ValueError, TypeError, tk.TclError):
                pass
            win.geometry(geometry)
        win.transient(self.root)
        self._set_icon(win)
        style_titlebar(win, self.c.header)
        win.after(80, lambda: _safe_grab(win))
        win.bind("<Escape>", lambda e: win.destroy())
        return win

    def show_settings(self) -> None:
        if self.busy_kind:
            self.info(self.tr("busy"))
            return
        c, t, cf = self.c, self.tr, self.cfg
        win = self._dialog(t("settings"), "760x760")
        btns = ttk.Frame(win, style="Panel.TFrame", padding=(18, 8, 18, 14))
        btns.pack(side="bottom", fill="x")
        sf = ScrollFrame(win, c.panel)
        fr = ttk.Frame(sf.inner, style="Panel.TFrame", padding=18)
        fr.pack(fill="both", expand=True)

        ttk.Label(fr, text=t("set_general"), style="Section.TLabel").pack(anchor="w")
        row = ttk.Frame(fr, style="Panel.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=t("set_language"), style="Panel.TLabel").pack(side="left")
        lang = ttk.Combobox(row, state="readonly", values=["Deutsch", "English"], width=12)
        lang.current(0 if cf["lang"] == "de" else 1)
        lang.pack(side="left", padx=8)
        ttk.Label(row, text=t("set_font"), style="Panel.TLabel").pack(side="left", padx=(20, 0))
        scales = [0.9, 1.0, 1.25, 1.5, 1.75, 2.0]
        fs_cb = ttk.Combobox(row, state="readonly", values=[f"{int(s * 100)} %" for s in scales], width=8)
        fs_cb.current(min(range(len(scales)), key=lambda i: abs(scales[i] - cf["font_scale"])))
        fs_cb.pack(side="left", padx=8)
        v_contrast = tk.BooleanVar(value=cf["high_contrast"])
        v_tts = tk.BooleanVar(value=cf["tts"])
        ttk.Checkbutton(fr, text=t("set_contrast"), variable=v_contrast).pack(anchor="w")
        ttk.Checkbutton(fr, text=t("set_tts"), variable=v_tts).pack(anchor="w")

        ttk.Label(fr, text=t("set_scan"), style="Section.TLabel").pack(anchor="w", pady=(14, 0))
        vars_ = {}
        for key, label in (("verify_bytes", "set_verify"), ("prefer_source_order", "set_order"),
                           ("move_sidecars", "set_sidecars"), ("protect_catalogs", "set_catalogs"),
                           ("skip_cloud_only", "set_cloud"), ("include_hidden", "set_hidden"),
                           ("find_folders", "set_folders"), ("find_similar", "set_similar"),
                           ("remove_empty_dirs", "set_emptydirs"), ("anonymize", "set_anon")):
            vars_[key] = tk.BooleanVar(value=cf[key])
            ttk.Checkbutton(fr, text=t(label), variable=vars_[key]).pack(anchor="w", pady=1)
        r2 = ttk.Frame(fr, style="Panel.TFrame")
        r2.pack(fill="x", pady=(8, 2))
        ttk.Label(r2, text=t("set_workers"), style="Panel.TLabel").pack(side="left")
        workers = tk.StringVar(value=str(cf["workers"]))
        ttk.Spinbox(r2, from_=0, to=16, textvariable=workers, width=5).pack(side="left", padx=8)
        r3 = ttk.Frame(fr, style="Panel.TFrame")
        r3.pack(fill="x", pady=2)
        ttk.Label(r3, text=t("set_minsize"), style="Panel.TLabel").pack(side="left")
        minsize = tk.StringVar(value=str(cf["min_size"]))
        ttk.Entry(r3, textvariable=minsize, width=10).pack(side="left", padx=8)
        ttk.Label(fr, text=t("set_excludes"), style="Panel.TLabel").pack(anchor="w", pady=(8, 2))
        ex = tk.Text(fr, height=5, bg=c.field, fg=c.fg, insertbackground=c.fg, relief="flat", font=self.f_mono)
        ex.insert("1.0", "\n".join(cf["excludes"]))
        ex.pack(fill="x")

        # F3: Ordnerregeln
        ttk.Label(fr, text=t("set_rules"), style="Section.TLabel").pack(anchor="w", pady=(14, 0))
        rule_lists = {}
        for key, label in (("prefer", "set_prefer"), ("avoid", "set_avoid")):
            ttk.Label(fr, text=t(label), style="Panel.TLabel").pack(anchor="w", pady=(6, 2))
            rrow = ttk.Frame(fr, style="Panel.TFrame")
            rrow.pack(fill="x")
            lb = self._listbox(rrow, 3)
            lb.pack(side="left", fill="x", expand=True)
            for d in cf.get(key, []):
                lb.insert("end", d)
            col = ttk.Frame(rrow, style="Panel.TFrame")
            col.pack(side="left", padx=(6, 0))

            def add(lb=lb):
                d = filedialog.askdirectory(parent=win, mustexist=True)
                if d and os.path.normpath(d) not in lb.get(0, "end"):
                    lb.insert("end", os.path.normpath(d))

            def rem(lb=lb):
                for i in reversed(lb.curselection()):
                    lb.delete(i)
            ttk.Button(col, text="+", width=3, command=add).pack()
            ttk.Button(col, text="–", width=3, command=rem).pack(pady=(4, 0))
            self._enable_drop(lb)
            rule_lists[key] = lb
        ttk.Label(fr, text=t("btn_diag"), style="Section.TLabel").pack(anchor="w", pady=(14, 4))
        ttk.Button(fr, text=t("btn_diag"), command=self.export_diagnostics).pack(anchor="w")


        def clear_cache():
            self.store.cache_clear()
            self.info("OK", parent=win)
        ttk.Button(btns, text=t("set_clear_cache"), command=clear_cache).pack(side="left")
        ttk.Button(btns, text=t("set_open_data"), command=lambda: open_with_default_app(self.data_dir)).pack(side="left", padx=6)

        def save():
            old = (cf["lang"], cf["high_contrast"], cf["font_scale"])
            cf["lang"] = "de" if lang.current() == 0 else "en"
            cf["font_scale"] = scales[fs_cb.current()]
            cf["high_contrast"] = bool(v_contrast.get())
            cf["tts"] = bool(v_tts.get())
            for k, v in vars_.items():
                cf[k] = bool(v.get())
            try:
                cf["workers"] = max(0, min(16, int(workers.get())))
            except ValueError:
                pass
            for key, lb in rule_lists.items():
                cf[key] = list(lb.get(0, "end"))
            try:
                cf["min_size"] = max(0, int(minsize.get()))
            except ValueError:
                pass
            cf["excludes"] = [x.strip() for x in ex.get("1.0", "end").splitlines() if x.strip()]
            self._sync_cfg()
            win.destroy()
            if old != (cf["lang"], cf["high_contrast"], cf["font_scale"]):
                self.build_ui()
        ttk.Button(btns, text=t("save"), style="Accent.TButton", command=save).pack(side="right")
        ttk.Button(btns, text=t("close"), command=win.destroy).pack(side="right", padx=6)

    def toggle_lang(self) -> None:
        self._sync_cfg()
        self.cfg["lang"] = "en" if self.cfg["lang"] == "de" else "de"
        config.save(self.data_dir, self.cfg)
        self.build_ui()

    def toggle_log(self) -> None:
        if self.log_visible:
            self.log_frame.pack_forget()
            self.log_btn.configure(text=self.tr("log") + " ▴")
        else:
            self.log_frame.pack(side="bottom", fill="x")
            self.log_btn.configure(text=self.tr("log") + " ▾")
        self.log_visible = not self.log_visible

    def _append_log(self, line: str, rebuild: bool = False) -> None:
        if not rebuild:
            self._log_lines.append(line)
            if len(self._log_lines) > 3000:
                self._log_lines = self._log_lines[-2000:]
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            if int(self.log_text.index("end-1c").split(".")[0]) > 2500:
                self.log_text.delete("1.0", "500.0")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except tk.TclError:
            pass

    # ================================================================ Start / Ende
    def startup_checks(self) -> None:
        t = self.tr
        # Haftungsausschluss einmal je Hauptversion bestaetigen lassen
        if not str(self.cfg.get("disclaimer_accepted", "")).startswith(APP_VERSION.split(".")[0] + "."):
            self.show_disclaimer(True)
        try:
            self.store.maintenance()
        except Exception:
            log.exception("Datenbankpflege fehlgeschlagen")
        try:
            notes = recover_all(self.store)
        except Exception as exc:
            log.exception("Wiederherstellung fehlgeschlagen")
            notes = [str(exc)]
        for n in notes:
            log.info("Wiederherstellung: %s", n)
        for run in self.store.runs_unfinished():
            open_n = len(self.store.journal_entries(run["id"], (J_PLANNED,)))
            if open_n == 0:
                self.store.run_finish(run["id"], "done", run.get("stats"))
                continue
            ans = self.ask_yes_no_cancel(t("resume_run_title"), t("resume_run", id=run["id"], open=open_n))
            if ans is None:
                continue
            if ans:
                self._resume_run(run)
                return
            for e in self.store.journal_entries(run["id"], (J_PLANNED,)):
                self.store.journal_set(e["id"], J_SKIPPED, error="verworfen")
            self.store.run_finish(run["id"], "cancelled", run.get("stats"))
        ses = self.store.session_latest()
        if not ses:
            return
        if ses["phase"] == "scanning":
            if self.ask_yes_no(t("resume_scan_title"), t("resume_scan")):
                self.session_id = ses["id"]
                self._scan(ScanOptions.from_dict(ses["options"]), ses["id"])
            else:
                self.store.session_update(ses["id"], phase="aborted")
        elif ses["phase"] == "review":
            self.session_id = ses["id"]
            self.session_stats = ses.get("stats") or {}
            self.groups = self.store.dupes_load(ses["id"])
            self.folder_groups = self.store.folders_load(ses["id"])
            self._index_groups()
            self._refresh_tree()
            if self.groups:
                self.status_var.set(t("loaded_session", groups=len(self.groups)))

    def on_close(self) -> None:
        try:
            self._sync_cfg()
            try:
                zoomed = str(self.root.state()) == "zoomed"
            except tk.TclError:
                zoomed = False
            self.cfg["maximized"] = zoomed
            if not zoomed:
                self.cfg["geometry"] = self.root.geometry()
            config.save(self.data_dir, self.cfg)
        except Exception:
            pass
        if self.busy_kind and self.control:
            if self.busy_kind == "scan":
                self.control.cancel()          # Cache wird beim Abbruch geschrieben
            else:
                self.control.pause()           # Journal bleibt offen -> Fortsetzen beim Start
            if self.worker:
                self.worker.join(timeout=5 if self.busy_kind == "scan" else 1.5)
            logging.getLogger("dateizwilling").info("Beendet waehrend %s – Fortsetzen beim naechsten Start", self.busy_kind)
            logging.shutdown()
            os._exit(0)
        try:
            self.store.close()
        except Exception:
            pass
        self.root.destroy()

    def _tk_exception(self, exc, val, tb) -> None:
        text = "".join(traceback.format_exception(exc, val, tb))
        log.error("Unbehandelter Fehler in der Oberflaeche:\n%s", text)
        try:
            self.info(self.tr("crash", err=f"{exc.__name__}: {val}"), "error")
        except Exception:
            pass


def _safe_grab(win: tk.Toplevel) -> None:
    try:
        if win.winfo_exists():
            win.grab_set()
    except tk.TclError:
        pass


def _thousands(n: int, lang: str) -> str:
    s = f"{n:,}"
    return s.replace(",", ".") if lang == "de" else s


def m_size(path: str) -> int:
    try:
        return os.path.getsize(fs(path))
    except OSError:
        return 1 << 62


def _short(s: str, n: int) -> str:
    return s if len(s) <= n else "…" + s[-(n - 1):]


def run_gui(store: Store, data_dir: str) -> None:
    if IS_WIN:
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SJK.DateiZwilling")
        except Exception:
            pass
    try:  # F5: Drag & Drop, falls tkinterdnd2 installiert ist
        from tkinterdnd2 import TkinterDnD  # type: ignore
        root = TkinterDnD.Tk()
        root._dz_dnd = True  # type: ignore[attr-defined]
    except Exception:
        root = tk.Tk()
    App(root, store, data_dir)
    root.mainloop()


def already_running_message(lang: str = "de") -> None:
    root = tk.Tk()
    root.withdraw()
    c = Palette(False)
    f = ("Segoe UI", 10) if IS_WIN else ("Helvetica", 13)
    dark_dialog(root, c, f, (f[0], f[1], "bold"), APP_NAME, Tr(lang)("already_running"), "warning",
                (("ok", "OK"),), "ok", "ok")
    root.destroy()
