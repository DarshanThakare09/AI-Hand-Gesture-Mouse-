@echo off
title AI Hand Gesture Virtual Mouse
color 0b
echo ========================================================
echo    Launching AI Hand Gesture Virtual Mouse...
echo ========================================================
echo.

IF NOT EXIST "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: py -3.11 -m venv venv
    echo and install requirements.
    pause
    exit /b
)

echo Starting application...
venv\Scripts\python.exe main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Program exited with error code %ERRORLEVEL%.
    pause
)
