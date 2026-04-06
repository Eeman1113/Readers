@echo off
title Readers - AI Reader Simulation
color 0E
cls

echo.
echo    ============================================
echo      Readers - AI Reader Simulation
echo      Up to 10,000 AI Readers Judge Your Book
echo    ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo    [ERROR] Python is not installed or not on PATH.
    echo    Download it from https://python.org
    echo    Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b
)

:: Check dependencies and install if missing
echo    Checking dependencies...
python -c "import rich" >nul 2>&1
if errorlevel 1 (
    echo    Installing rich...
    pip install rich >nul 2>&1
)
python -c "import dotenv" >nul 2>&1
if errorlevel 1 (
    echo    Installing python-dotenv...
    pip install python-dotenv >nul 2>&1
)
echo    Dependencies OK.
echo.

:: Check for .env
if not exist ".env" (
    echo    [NOTE] No .env file found.
    echo    For cloud providers (Gemini, OpenAI, etc), copy .env.example to .env
    echo    and add your API key. Ollama works without a key.
    echo.
)

:: Get book file
echo    ============================================
echo      STEP 1: Your Book Description
echo    ============================================
echo.
echo    Enter the path to your book description file.
echo    (e.g., my_book.txt or examples\sample_book.txt)
echo.
set /p BOOKFILE="    Book file: "

if not exist "%BOOKFILE%" (
    echo.
    echo    [ERROR] File not found: %BOOKFILE%
    echo    Make sure the file exists and try again.
    echo.
    pause
    exit /b
)

:: Get provider
echo.
echo    ============================================
echo      STEP 2: Choose AI Provider
echo    ============================================
echo.
echo    1. Ollama     (FREE - runs on your computer, slower)
echo    2. Gemini     (FAST - ~$0.25 per 1,000 readers, needs API key)
echo    3. OpenAI     (FAST - ~$0.70 per 1,000 readers, needs API key)
echo    4. Anthropic  (FAST - ~$1.00 per 1,000 readers, needs API key)
echo.
set /p PROVIDER_CHOICE="    Choose (1-4): "

if "%PROVIDER_CHOICE%"=="1" set PROVIDER=ollama
if "%PROVIDER_CHOICE%"=="2" set PROVIDER=gemini
if "%PROVIDER_CHOICE%"=="3" set PROVIDER=openai
if "%PROVIDER_CHOICE%"=="4" set PROVIDER=anthropic
if not defined PROVIDER set PROVIDER=ollama

:: Install provider SDK if needed
if "%PROVIDER%"=="ollama" pip install ollama >nul 2>&1
if "%PROVIDER%"=="gemini" pip install google-genai >nul 2>&1
if "%PROVIDER%"=="openai" pip install openai >nul 2>&1
if "%PROVIDER%"=="anthropic" pip install anthropic >nul 2>&1

:: Get reader count
echo.
echo    ============================================
echo      STEP 3: How Many Readers?
echo    ============================================
echo.
echo    Recommended:
echo      100   = Quick test (~2-5 min)
echo      500   = Solid sample (~10-15 min)
echo      1000  = Full simulation (~15-30 min)
echo      5000  = Deep analysis (~1-2 hours)
echo      10000 = Maximum depth (~2-4 hours)
echo.
set /p READERS="    Number of readers (default 1000): "
if "%READERS%"=="" set READERS=1000

:: Get rounds
echo.
echo    ============================================
echo      STEP 4: How Many Social Rounds?
echo    ============================================
echo.
echo    Round 1 = Initial reactions (always runs)
echo    Round 2+ = Readers react to each other
echo.
echo    Recommended: 3-5 rounds for rich results
echo.
set /p ROUNDS="    Number of rounds (1-30, default 3): "
if "%ROUNDS%"=="" set ROUNDS=3

:: Confirm and run
echo.
echo    ============================================
echo      READY TO RUN
echo    ============================================
echo.
echo      Book:     %BOOKFILE%
echo      Provider: %PROVIDER%
echo      Readers:  %READERS%
echo      Rounds:   %ROUNDS%
echo.
echo    The simulation will start now. A gorgeous HTML report
echo    will open in your browser when complete.
echo.
pause

echo.
echo    Starting Readers...
echo.

python readers.py --file "%BOOKFILE%" --provider %PROVIDER% --readers %READERS% --rounds %ROUNDS%

echo.
echo    ============================================
echo      SIMULATION COMPLETE!
echo    ============================================
echo.
echo    Your report has been saved to the output/ folder
echo    and should have opened in your browser.
echo.
echo    Run again? Just double-click this file!
echo.
pause
