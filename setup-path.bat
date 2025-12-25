@echo off
REM Onyx Setup - Add Onyx to Windows PATH
REM Run this script as Administrator

echo ============================================
echo Onyx v2.0.0 Setup
echo ============================================
echo.

REM Get the current directory (where Onyx is installed)
set "ONYX_DIR=%~dp0"
set "ONYX_DIR=%ONYX_DIR:~0,-1%"

echo Installing Onyx to system PATH...
echo Directory: %ONYX_DIR%
echo.

REM Check if already in PATH
echo %PATH% | findstr /C:"%ONYX_DIR%" >nul
if %ERRORLEVEL% EQU 0 (
    echo Onyx is already in your PATH!
    goto :end
)

REM Add to User PATH (doesn't require admin)
echo Adding to User PATH...
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "CURRENT_PATH=%%b"

if "%CURRENT_PATH%"=="" (
    setx PATH "%ONYX_DIR%"
) else (
    setx PATH "%CURRENT_PATH%;%ONYX_DIR%"
)

echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo You can now use these commands from anywhere:
echo   onyx start
echo   onyx stop
echo   onyx status
echo.
echo IMPORTANT: Close and reopen your terminal for changes to take effect!
echo ============================================
echo.
pause

:end
exit /b 0
