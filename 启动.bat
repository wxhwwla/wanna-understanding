@echo off
chcp 65001 >nul
title Wanna Understanding - AI 代码审阅员

echo ============================================
echo   Wanna Understanding
echo   AI 代码审阅员 - 只读不写，零操作，实时分析
echo ============================================
echo.

:: 确保在仓库根目录
cd /d "%~dp0"

:: 优先使用 pythonw（无控制台窗口，适合后台常驻）
if exist ".venv\Scripts\pythonw.exe" (
    set PYTHON=.venv\Scripts\pythonw.exe
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=pythonw
)

echo [信息] 启动中（托盘右键可退出）...
start "" %PYTHON% -m wanna_understanding

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 启动失败，错误码: %ERRORLEVEL%
    echo 请安装依赖后重试: pip install -e ".[dev,ocr]"
    pause
)
