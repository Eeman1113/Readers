@echo off
title Readers
color 07
cls

echo.
echo    Readers
echo    -----------------------------------------------
echo    Up to 500,000 AI Readers Judge Your Book
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo    [ERROR] Python is not installed or not on PATH.
    echo    Download it from https://python.org
    echo.
    pause
    exit /b
)

:: Check dependencies
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
echo    OK.
echo.

:: Check for .env
if not exist ".env" (
    echo    No .env file found. Ollama works without a key.
    echo    For cloud providers, copy .env.example to .env and add your key.
    echo.
)

:: Get book file
echo    -----------------------------------------------
echo    1. Book Description
echo    -----------------------------------------------
echo.
echo    Enter the path to your book description file.
echo.
set /p BOOKFILE="    File: "

if not exist "%BOOKFILE%" (
    echo.
    echo    [ERROR] File not found: %BOOKFILE%
    echo.
    pause
    exit /b
)

:: Get provider
echo.
echo    -----------------------------------------------
echo    2. AI Provider
echo    -----------------------------------------------
echo.
echo    1. Ollama     (free, local)
echo    2. Gemini     (recommended, fast)
echo    3. OpenAI     (GPT-4o-mini)
echo    4. Anthropic  (Claude)
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
echo    -----------------------------------------------
echo    3. Reader Count
echo    -----------------------------------------------
echo.
echo      100  = Quick test
echo      1000 = Standard run
echo      5000 = Deep analysis
echo.
set /p READERS="    Readers (default 1000): "
if "%READERS%"=="" set READERS=1000

:: Get rounds
echo.
echo    -----------------------------------------------
echo    4. Social Rounds
echo    -----------------------------------------------
echo.
echo    Round 1 = Initial reactions
echo    Round 2+ = Social dynamics
echo.
set /p ROUNDS="    Rounds (default 3): "
if "%ROUNDS%"=="" set ROUNDS=3

:: Run
echo.
echo    -----------------------------------------------
echo    Starting simulation...
echo    -----------------------------------------------
echo.

python readers.py --file "%BOOKFILE%" --provider %PROVIDER% --readers %READERS% --rounds %ROUNDS%

echo.
echo    Done. Report saved to output/ folder.
echo.
pause
