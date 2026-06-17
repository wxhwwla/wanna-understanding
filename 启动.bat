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

:: 检查虚拟环境
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo [信息] 启动中...
%PYTHON% -m wanna_understanding

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 程序异常退出，错误码: %ERRORLEVEL%
    echo 请安装依赖后重试: pip install -e ".[dev]"
    pause
)
