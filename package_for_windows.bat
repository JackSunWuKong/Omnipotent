@echo off
title UniversalKey Builder
cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.10-3.12 and check Add to PATH.
    pause
    exit /b
)

python build_exe.py
pause
