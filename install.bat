@echo off
:: ============================================================
::  XCM Language Engine - Windows Installer
:: ============================================================

set GITHUB_USER=Sakebi-C
set REPO=xcm-lang
set RAW_URL=https://raw.githubusercontent.com/%GITHUB_USER%/%REPO%/main/xcm.py
set INSTALL_DIR=%USERPROFILE%\xcm-lang
set INSTALL_FILE=%INSTALL_DIR%\xcm.py
set BAT_FILE=%INSTALL_DIR%\xcm.bat

echo.
echo ============================================
echo        XCM Language Engine Installer
echo ============================================
echo.

:: Check Python
echo   Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   Python not found!
    echo   Download from: https://python.org/downloads
    echo   Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo   Found: %%i
echo.

:: Create install directory
echo   Creating install directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Download xcm.py
echo   Downloading XCM...
powershell -Command "Invoke-WebRequest -Uri '%RAW_URL%' -OutFile '%INSTALL_FILE%'" >nul 2>&1
if not exist "%INSTALL_FILE%" (
    echo   Download failed! Check your internet connection.
    pause
    exit /b 1
)
echo   Download successful!
echo.

:: Create xcm.bat wrapper
echo   Creating xcm command...
echo @echo off > "%BAT_FILE%"
echo python "%INSTALL_FILE%" %%* >> "%BAT_FILE%"

:: Add to PATH
echo   Adding to PATH...
powershell -Command "[Environment]::SetEnvironmentVariable('PATH', $env:PATH + ';%INSTALL_DIR%', 'User')" >nul 2>&1

echo   Installation successful!
echo.
echo ============================================
echo   XCM installed to: %INSTALL_DIR%
echo   Restart your terminal, then run:
echo     xcm run file.xcm
echo     xcm version
echo ============================================
echo.
pause
