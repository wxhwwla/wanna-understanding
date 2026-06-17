@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

if not defined TCL_LIBRARY (
    for /f "delims=" %%i in ('"%PYTHON%" -c "import sys; print(sys.base_prefix)"') do set "PY_BASE=%%i"
    if exist "!PY_BASE!\tcl\tcl8.6\init.tcl" (
        set "TCL_LIBRARY=!PY_BASE!\tcl\tcl8.6"
        set "TK_LIBRARY=!PY_BASE!\tcl\tk8.6"
    )
)

echo Wanna Understanding - debug mode (console stays open on error)
echo.
"%PYTHON%" -m wanna_understanding
set "RC=!ERRORLEVEL!"
echo.
if not "!RC!"=="0" (
    echo Exit code: !RC!
    echo If missing modules, run: 修复venv.bat
)
pause
