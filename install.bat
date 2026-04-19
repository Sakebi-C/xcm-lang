@echo off
:: ============================================================
::  XCM Language Engine - Windows Installer
::  Otomatis download dan install xcm.exe
:: ============================================================

set GITHUB_USER=Sakebi-C
set REPO=xcm-lang
set VERSION=v1.0.0
set DOWNLOAD_URL=https://github.com/%GITHUB_USER%/%REPO%/releases/download/%VERSION%/xcm.exe
set INSTALL_DIR=C:\xcm
set INSTALL_FILE=%INSTALL_DIR%\xcm.exe

echo.
echo ============================================
echo        XCM Language Engine Installer
echo        Version %VERSION%
echo ============================================
echo.

:: Check admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] Run as Administrator for best results.
    echo   [!] Trying to install without admin...
    echo.
)

:: Create install directory
echo   [1/4] Creating install directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if %errorlevel% neq 0 (
    echo   Failed to create %INSTALL_DIR%
    echo   Try running as Administrator.
    pause
    exit /b 1
)
echo         Done: %INSTALL_DIR%
echo.

:: Download xcm.exe
echo   [2/4] Downloading xcm.exe...
powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%INSTALL_FILE%'" >nul 2>&1
if not exist "%INSTALL_FILE%" (
    echo   Download failed!
    echo   Check your internet connection.
    echo   Or download manually from:
    echo   https://github.com/%GITHUB_USER%/%REPO%/releases
    pause
    exit /b 1
)
echo         Done!
echo.

:: Add to PATH
echo   [3/4] Adding to PATH...
powershell -Command "[Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH','Machine') + ';%INSTALL_DIR%', 'Machine')" >nul 2>&1
if %errorlevel% neq 0 (
    :: Try user PATH if machine PATH fails
    powershell -Command "[Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH','User') + ';%INSTALL_DIR%', 'User')" >nul 2>&1
)
echo         Done!
echo.

:: Verify
echo   [4/4] Verifying installation...
"%INSTALL_FILE%" version >nul 2>&1
if %errorlevel% equ 0 (
    echo         Done!
    echo.
    echo ============================================
    echo   XCM %VERSION% installed successfully!
    echo.
    echo   IMPORTANT: Restart your terminal first!
    echo   Then run: xcm run file.xcm
    echo ============================================
) else (
    echo   Something went wrong!
    echo   Try running xcm manually:
    echo   %INSTALL_FILE% version
)
echo.
pause
