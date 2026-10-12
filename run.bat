@echo off
title DataPilot AI - Data Studio
cd /d "%~dp0"
echo ========================================
echo       DataPilot AI - Data Studio
echo ========================================
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
if not exist .venv (
  echo [1/3] Creating Python virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto failed
)
call .venv\Scripts\activate.bat
echo [2/3] Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo [3/3] Starting DataPilot AI...
echo Open http://127.0.0.1:5000 in your browser.
start "" http://127.0.0.1:5000
python app.py
goto end
:failed
echo.
echo Setup failed. Check that Python 3.10+ is installed and added to PATH.
pause
:end
