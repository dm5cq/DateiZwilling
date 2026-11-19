"""Rauchtest der Oberflaeche ohne Bildschirm: tkinter wird durch eine
Attrappe ersetzt. Prueft, dass Aufbau, Scan-Ablauf, Auswahl, Umschalten,
Archivieren, Rueckgaengig, Sprachwechsel und Einstellungen ohne Python-Fehler
durchlaufen (NameError, AttributeError, falsche Schluessel …)."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ----------------------------------------------------------------- Attrappe
class TclError(Exception):
    pass


class Var:
    default = ""

    def __init__(self, master=None, value=None, **kw):
        self._v = self.default if value is None else value
        self._cb = []

    def get(self):
        return self._v

    def set(self, v):
        self._v = v
        for cb in self._cb:
            cb()

    def trace_add(self, mode, cb):
        self._cb.append(cb)


class W:
    """Generisches Widget."""
    _counter = 0

    def __init__(self, *a, **kw):
        self._opts = dict(kw)
        self._items = []
        self._sel = ()
        self._binds = {}
        self._children = []
        parent = a[0] if a and isinstance(a[0], W) else None
        if parent is not None:
            parent._children.append(self)

    def __getattr__(self, name):
        def f(*a, **k):
            return None
        return f

    def configure(self, *a, **kw):
        self._opts.update(kw)
    config = configure

    def cget(self, k):
        return self._opts.get(k, 200 if k in ("width", "height") else "determinate")

    def bind(self, ev, fn=None, *a):
        self._binds[ev] = fn

    def winfo_children(self):
        return list(self._children)

    def destroy(self):
        pass

    def winfo_exists(self):
        return True

    def geometry(self, *a):
        return "1320x840+0+0"

    def after(self, ms, fn=None, *a):
        return "after#1"

    # Listbox
    def insert(self, idx, *vals, **kw):
        self._items.extend(vals)

    def get(self, a=None, b=None):
        if a == 0:
            return tuple(self._items)
        return ""

    def delete(self, *a):
        if a and isinstance(a[0], int):
            del self._items[a[0]]
        elif a and a[0] in ("1.0",):
            pass

    def curselection(self):
        return self._sel

    def size(self):
        return len(self._items)

    def current(self, i=None):
        if i is None:
            return self._opts.get("_cur", 0)
        self._opts["_cur"] = i

    def index(self, *a):
        return "1.0"

    def state(self, *a):
        return ()


class Tree(W):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.rows = {}
        self.order = []
        self._focus = ""
        self._selection = ()

    def insert(self, parent, idx, iid=None, **kw):
        self.rows[iid] = dict(kw, parent=parent)
        self.order.append(iid)
        return iid

    def exists(self, iid):
        return iid in self.rows

    def item(self, iid, option=None, **kw):
        if option == "values":
            return self.rows[iid].get("values", ())
        self.rows[iid].update(kw)

    def get_children(self, item=""):
        return [i for i in self.order if self.rows.get(i, {}).get("parent") == item]

    def delete(self, *iids):
        for i in iids:
            for c in [k for k, v in self.rows.items() if v["parent"] == i]:
                self.delete(c)
            self.rows.pop(i, None)
            if i in self.order:
                self.order.remove(i)

    def focus(self, iid=None):
        if iid is None:
            return self._focus
        self._focus = iid

    def selection(self):
        return self._selection


def install_fake_tk():
    tk = types.ModuleType("tkinter")
    for n in ("Tk", "Toplevel", "Frame", "Label", "Canvas", "Text", "Listbox", "PhotoImage", "Misc", "Button"):
        setattr(tk, n, type(n, (W,), {}))
    tk.TclError = TclError
    tk.StringVar = Var
    tk.BooleanVar = type("BooleanVar", (Var,), {"default": False})
    tk.IntVar = type("IntVar", (Var,), {"default": 0})
    ttk = types.ModuleType("tkinter.ttk")
    for n in ("Frame", "Label", "Button", "Entry", "Combobox", "Checkbutton", "Radiobutton",
              "Progressbar", "Scrollbar", "PanedWindow", "Spinbox", "Style"):
        setattr(ttk, n, type(n, (W,), {}))
    ttk.Treeview = Tree
    fd = types.ModuleType("tkinter.filedialog")
    fd.askdirectory = lambda **k: ""
    fd.asksaveasfilename = lambda **k: ""
    mb = types.ModuleType("tkinter.messagebox")
    mb.answers = {"askyesno": True, "askyesnocancel": None}
    mb.calls = []
    for n in ("showinfo", "showwarning", "showerror"):
        setattr(mb, n, lambda *a, _n=n, **k: mb.calls.append((_n, a)))
    mb.askyesno = lambda *a, **k: mb.answers["askyesno"]
    mb.askyesnocancel = lambda *a, **k: mb.answers["askyesnocancel"]
    font = types.ModuleType("tkinter.font")
    font.nametofont = lambda n: W()
    tk.ttk, tk.filedialog, tk.messagebox, tk.font = ttk, fd, mb, font
    sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk, "tkinter.filedialog": fd,
                        "tkinter.messagebox": mb, "tkinter.font": font})
    sys.modules.pop("PIL.ImageTk", None)
    return mb


class GuiSmoke(unittest.TestCase):
    def setUp(self):
        self.mb = install_fake_tk()
        for m in [m for m in sys.modules if m.startswith("dateizwilling.gui")]:
            del sys.modules[m]
        from dateizwilling import gui
        from dateizwilling.state import Store
        self.gui = gui
        self.dialogs = []

        def fake_dialog(parent, c, font, bold, title, text, kind="info", buttons=(), default="ok",
                        cancel_value=None):
            self.dialogs.append((kind, text))
            return default
        gui.dark_dialog = fake_dialog
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, "daten")
        self.store = Store(self.data)
        a, b = os.path.join(self.tmp, "A"), os.path.join(self.tmp, "B")
        os.makedirs(a)
        os.makedirs(os.path.join(b, "sub"))
        payload = os.urandom(150_000)
        for p in (os.path.join(a, "x.pdf"), os.path.join(b, "sub", "x.pdf"), os.path.join(b, "z.pdf")):
            with open(p, "wb") as fh:
                fh.write(payload)
        self.a, self.b = a, b

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wait(self, app):
        for _ in range(200):
            if app.busy_kind is None:
                return
            app.poll()
            time.sleep(0.05)
        self.fail("Hintergrundarbeit endet nicht")

    def test_full_flow(self):
        app = self.gui.App(self.gui.tk.Tk(), self.store, self.data)
        app.startup_checks()
        app.src_list._items = [self.a, self.b]
        app.archive_var.set(os.path.join(self.tmp, "Archiv"))
        app.start_scan()
        self.wait(app)
        self.assertEqual(len(app.groups), 1, self.dialogs)
        gid = app.groups[0]["gid"]
        # Auswahl + Umschalten + Original festlegen
        app.tree.focus(f"g{gid}:2")
        app._on_select()
        app.set_original()
        self.assertTrue(app.groups[0]["members"][2]["keep"])
        app.tree.focus(f"g{gid}:0")
        app.toggle_keep()
        self.assertTrue(app.groups[0]["members"][0]["keep"])
        app.toggle_keep()
        # Archivieren
        app.archive(True)
        self.wait(app)
        archived = [m for m in app.groups[0]["members"] if m.get("state") == "archived"]
        self.assertEqual(len(archived), 2, self.dialogs)
        # Bericht, Sprache, Einstellungen, Info
        app.toggle_lang()
        app.toggle_log()
        app.show_info()
        app.show_license()
        app.show_disclaimer(False)
        app.show_settings()
        app.show_purge()
        app.show_stats()
        app.show_archive_browser()
        app.show_schedule()
        # Ansichten wechseln (doppelte Ordner / nahezu gleiche Dokumente) und Seiten
        for k in (1, 2, 0):
            app.view_cb.current(k)
            app._change_view()
        app._goto_page(1)
        app._goto_page(-1)
        # Rueckgaengig
        app.undo_last()
        self.wait(app)
        self.assertTrue(all(m.get("state") == "open" for m in app.groups[0]["members"]))
        self.assertFalse([d for d in self.dialogs if d[0] == "error"], self.dialogs)

    def test_folder_view_archive(self):
        app = self.gui.App(self.gui.tk.Tk(), self.store, self.data)
        app.src_list._items = [self.a, self.b]
        app.archive_var.set(os.path.join(self.tmp, "Archiv"))
        app.start_scan()
        self.wait(app)
        self.assertEqual(len(app.folder_groups), 1, self.dialogs)   # A und B/sub sind gleich
        app.view_cb.current(1)
        app._change_view()
        fg = app.folder_groups[0]
        arch_idx = next(i for i, f in enumerate(fg["folders"]) if not f["keep"])
        app.tree.focus(f"f{fg['fgid']}:{arch_idx}")
        app.set_original()                                     # anderen Ordner zum Original machen
        self.assertTrue(fg["folders"][arch_idx]["keep"])
        app.archive(True)
        self.wait(app)
        archived = [m for g in app.groups for m in g["members"] if m.get("state") == "archived"]
        self.assertEqual(len(archived), 1, self.dialogs)
        self.assertFalse([d for d in self.dialogs if d[0] in ("error", "warning")], self.dialogs)
        self.assertFalse(self.mb.calls, "native Windows-Meldungsfenster verwendet")

    def test_restart_loads_session(self):
        app = self.gui.App(self.gui.tk.Tk(), self.store, self.data)
        app.src_list._items = [self.a, self.b]
        app.archive_var.set(os.path.join(self.tmp, "Archiv"))
        app.start_scan()
        self.wait(app)
        app2 = self.gui.App(self.gui.tk.Tk(), self.store, self.data)
        app2.startup_checks()
        self.assertEqual(len(app2.groups), 1)


if __name__ == "__main__":
    unittest.main()


class DialogSmoke(unittest.TestCase):
    def test_dark_dialog_builds(self):
        install_fake_tk()
        for m in [m for m in sys.modules if m.startswith("dateizwilling.gui")]:
            del sys.modules[m]
        from dateizwilling import gui
        c = gui.Palette(False)
        root = gui.tk.Tk()
        v = gui.dark_dialog(root, c, ("Segoe UI", 10), ("Segoe UI", 10, "bold"), "T", "Text", "question",
                            (("yes", "Ja"), ("no", "Nein")), "yes", "no")
        self.assertEqual(v, "no")   # Attrappe schliesst sofort -> Abbruchwert
        sf = gui.ScrollFrame(root, c.panel)
        sf._update_bar()
