@echo off
title Readers - Starting...
color 0E

echo.
echo    ============================================
echo      Readers - AI Reader Simulation
echo    ============================================
echo.
echo    Checking Python installation...

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo    ERROR: Python is not installed!
    echo    Please install Python 3.10+ from https://python.org
    echo    Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo    Python found. Installing required packages...
echo.

pip install rich python-dotenv google-genai openai anthropic >nul 2>&1

echo    Packages ready. Launching Readers GUI...
echo.

python "%~dp0readers_gui.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo    Something went wrong. Trying command-line mode instead...
    echo.
    call "%~dp0run_readers.bat"
)

pause
