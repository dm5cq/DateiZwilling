#!/bin/bash
# DateiZwilling – macOS-App bauen (Apple Silicon und Intel)
# Voraussetzung: Python 3.10+ von python.org (enthaelt Tcl/Tk)
#   oder Homebrew:  brew install python python-tk
set -euo pipefail
cd "$(dirname "$0")"
echo "=== DateiZwilling 2.0.0 – macOS-Build ==="
PY=${PYTHON:-python3}
$PY -c "import sys; assert sys.version_info >= (3,10)" || { echo "Python 3.10+ benoetigt"; exit 1; }
$PY -c "import tkinter" || { echo "tkinter fehlt (brew install python-tk)"; exit 1; }
[ -x .venv/bin/python ] || $PY -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt
python -m pip freeze > build-lock.txt   # S9: exakte Paketstaende
echo "Tests …"
python -m unittest discover -s tests || { read -r -p "Tests fehlgeschlagen – trotzdem bauen? (j/N) " a; [ "$a" = "j" ] || exit 1; }
pyinstaller --noconfirm --clean --windowed --name DateiZwilling \
  --icon assets/icon.icns --add-data "assets:assets" \
  --collect-all tkinterdnd2 --collect-all pypdfium2 \
  --osx-bundle-identifier de.kaiser-burghausen.dateizwilling DateiZwilling.py
# Signatur: mit Entwickler-ID (DZ_SIGN_ID gesetzt) oder ad-hoc fuer den lokalen Start
codesign --force --deep --sign "${DZ_SIGN_ID:--}" dist/DateiZwilling.app || true
# DMG zum Weitergeben
hdiutil create -volname DateiZwilling -srcfolder dist/DateiZwilling.app -ov -format UDZO dist/DateiZwilling-2.0.0.dmg || true
shasum -a 256 dist/DateiZwilling-2.0.0.dmg > dist/DateiZwilling-2.0.0.dmg.sha256.txt || true
echo "Fertig: dist/DateiZwilling.app  und  dist/DateiZwilling-2.0.0.dmg"
echo "Hinweis: Beim ersten Start Rechtsklick > Oeffnen. Fuer volle Ordnerzugriffe ggf."
echo "Systemeinstellungen > Datenschutz > Festplattenvollzugriff fuer DateiZwilling erlauben."
