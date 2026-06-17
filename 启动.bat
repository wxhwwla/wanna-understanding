@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
    set "PYTHON=.venv\Scripts\pythonw.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=pythonw"
)

if not defined TCL_LIBRARY (
    if exist ".venv\Scripts\python.exe" (
        for /f "delims=" %%i in ('".venv\Scripts\python.exe" -c "import sys; print(sys.base_prefix)"') do set "PY_BASE=%%i"
        if exist "!PY_BASE!\tcl\tcl8.6\init.tcl" (
            set "TCL_LIBRARY=!PY_BASE!\tcl\tcl8.6"
            set "TK_LIBRARY=!PY_BASE!\tcl\tk8.6"
        )
    )
)

echo Wanna Understanding - starting (quit from tray menu)...
start "" "%PYTHON%" -m wanna_understanding

if errorlevel 1 (
    echo.
    echo Startup failed. Try: pip install -e ".[dev,ocr]"
    pause
)
