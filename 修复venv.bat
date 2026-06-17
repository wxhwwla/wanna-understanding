@echo off
chcp 65001 >nul
title 修复 Wanna Understanding 虚拟环境

echo ============================================
echo   修复虚拟环境 pip（重建 .venv）
echo ============================================
echo.

cd /d "%~dp0"

if exist ".venv" (
    echo [信息] 删除损坏的 .venv ...
    rmdir /s /q ".venv"
)

echo [信息] 创建新虚拟环境 ...
set PYTHONUTF8=1
python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
)

echo [信息] 安装依赖 ...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev,ocr]"

if %ERRORLEVEL% NEQ 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo [完成] 虚拟环境已修复。可运行: 启动.bat
pause
