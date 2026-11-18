"""Startpunkt von DateiZwilling (GUI oder --cli)."""
from __future__ import annotations

import faulthandler
import logging
import logging.handlers
import os
import sys
import threading
import traceback


def _setup_logging(data_dir: str):
    log_dir = os.path.join(data_dir, "Protokolle")
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger("dateizwilling")
    root.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(os.path.join(log_dir, "dateizwilling.log"),
                                              maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s"))
    root.addHandler(fh)
    # Absturzprotokoll auch fuer harte Abstuerze (Segfault o. Ae.)
    crash = open(os.path.join(log_dir, "absturz.log"), "a", encoding="utf-8")
    faulthandler.enable(crash)

    def hook(exc_type, exc, tb):
        root.critical("Unbehandelte Ausnahme:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))

    def thread_hook(args):
        root.critical("Unbehandelte Ausnahme im Thread %s:\n%s", args.thread.name if args.thread else "?",
                      "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))
    sys.excepthook = hook
    threading.excepthook = thread_hook
    return crash


def main() -> int:
    from dateizwilling import APP_VERSION, config
    from dateizwilling.pathutil import InstanceLock, data_dir
    from dateizwilling.state import Store

    folder = data_dir()
    crash_fh = _setup_logging(folder)
    log = logging.getLogger("dateizwilling")
    cli = len(sys.argv) > 1 and (sys.argv[1] == "--cli" or sys.argv[1] in
                                 ("scan", "resume", "runs", "undo", "purge", "-h", "--help"))
    log.info("DateiZwilling %s startet (%s), Daten: %s", APP_VERSION, "CLI" if cli else "GUI", folder)

    lock = InstanceLock(folder)
    if not lock.acquire():
        if cli:
            print("DateiZwilling laeuft bereits.")
        else:
            from dateizwilling.gui import already_running_message
            already_running_message(config.load(folder).get("lang", "de"))
        return 3
    store = Store(folder)
    try:
        if cli:
            from dateizwilling.cli import main as cli_main
            args = [a for a in sys.argv[1:] if a != "--cli"]
            return cli_main(args, store)
        from dateizwilling.gui import run_gui
        run_gui(store, folder)
        return 0
    finally:
        try:
            store.close()
        except Exception:
            pass
        lock.release()
        log.info("DateiZwilling beendet")
        crash_fh.close()


if __name__ == "__main__":
    sys.exit(main())
