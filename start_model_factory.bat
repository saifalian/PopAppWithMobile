@echo off
title ModelFactory Launcher
echo ⚡ Starting ModelFactory...
echo 🧠 Checking hardware and environment...

:: Use the local virtual environment which has PyQt6 and GPU support
set PYTHON_EXE=d:\pop\venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo.
    echo ❌ ERROR: Virtual environment not found at:
    echo %PYTHON_EXE%
    echo Please ensure the environment exists and try again.
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERROR: The application failed to start (Exit Code: %ERRORLEVEL%).
    echo.
    pause
)
