@echo off
setlocal
cd /d "%~dp0"
title DateiZwilling - Windows-Build
echo.
echo  ===  DateiZwilling 1.0.0  -  portable Windows-EXE bauen  ===
echo.

rem --- Python suchen (py-Launcher bevorzugt) ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo FEHLER: Python 3.10 oder neuer wurde nicht gefunden.
  echo Bitte von https://www.python.org installieren ^(Haken bei "Add python.exe to PATH"^).
  goto :fehler
)
%PY% -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" || (echo FEHLER: Python 3.10+ benoetigt & goto :fehler)
%PY% -c "import tkinter" || (echo FEHLER: tkinter fehlt - Python von python.org mit "tcl/tk" installieren & goto :fehler)

rem --- virtuelle Umgebung ---
if not exist ".venv\Scripts\python.exe" (
  echo Erzeuge virtuelle Umgebung ...
  %PY% -m venv .venv || goto :fehler
)
call ".venv\Scripts\activate.bat" || goto :fehler
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto :fehler

rem --- automatische Tests ---
echo.
echo Fuehre automatische Tests aus ...
python -m unittest discover -s tests
if errorlevel 1 (
  echo.
  echo ACHTUNG: Mindestens ein Test ist fehlgeschlagen. Bitte die Ausgabe oben zurueckmelden.
  choice /C JN /M "Trotzdem bauen"
  if errorlevel 2 goto :fehler
)

rem --- EXE bauen ---
echo.
echo Baue DateiZwilling.exe ...
pyinstaller --noconfirm --clean --onefile --windowed --name DateiZwilling --icon "assets\icon.ico" --add-data "assets;assets" --version-file version_info.txt DateiZwilling.py || goto :fehler

echo.
echo  FERTIG:  dist\DateiZwilling.exe
echo  Die EXE ist portabel. Einstellungen, Cache und Protokolle landen im Ordner
echo  "DateiZwilling-Daten" neben der EXE.
echo.
explorer dist
pause
exit /b 0

:fehler
echo.
echo  BUILD FEHLGESCHLAGEN - bitte die Meldungen oben zurueckmelden.
pause
exit /b 1
