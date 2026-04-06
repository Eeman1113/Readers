@echo off
title Readers
color 07

echo.
echo    Readers
echo    -----------------------------------------------
echo.
echo    Checking Python...

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo    ERROR: Python is not installed.
    echo    Install Python 3.10+ from https://python.org
    echo.
    pause
    exit /b 1
)

echo    Installing packages...
echo.

pip install rich python-dotenv google-genai openai anthropic >nul 2>&1

echo    Ready. Launching GUI...
echo.

python "%~dp0readers_gui.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo    GUI failed. Trying command-line mode...
    echo.
    call "%~dp0run_readers.bat"
)

pause
