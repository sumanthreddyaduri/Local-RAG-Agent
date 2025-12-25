@echo off
REM Onyx CLI - Unified command interface
REM Usage: .\onyx [start|stop|status]

set "CMD=%1"

if "%CMD%"=="" set "CMD=start"
if "%CMD%"=="start" goto :start
if "%CMD%"=="stop" goto :stop
if "%CMD%"=="status" goto :status
if "%CMD%"=="setup" goto :setup

echo Unknown command: %CMD%
echo Usage: .\onyx [start^|stop^|status^|setup]
exit /b 1

:start
echo Starting Onyx v2.0.0...
python start_app.py
exit /b 0

:stop
echo Stopping Onyx...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID"') do (
    wmic process where "ProcessId=%%a and CommandLine like '%%start_app.py%%'" delete >nul 2>&1
)
echo Onyx stopped.
timeout /t 1 >nul
exit /b 0

:status
echo Checking Onyx status...
echo.
set "FOUND=0"
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID"') do (
    for /f %%b in ('wmic process where "ProcessId=%%a" get CommandLine /format:list 2^>nul ^| findstr /C:"start_app.py"') do (
        set "FOUND=1"
        echo [92mOnyx is RUNNING[0m
        echo PID: %%a
        echo URL: http://localhost:8501
        goto :statusend
    )
)
:statusend
if "%FOUND%"=="0" (
    echo [91mOnyx is NOT running[0m
    echo To start: .\onyx start
)
exit /b 0

:setup
echo ============================================
echo Onyx v2.0.0 Setup
echo ============================================
echo.
echo This will add Onyx to your Windows PATH so you can
echo use 'onyx' commands from anywhere without '.\'
echo.

REM Get the current directory
set "ONYX_DIR=%~dp0"
set "ONYX_DIR=%ONYX_DIR:~0,-1%"

REM Check if already in PATH
echo %PATH% | findstr /C:"%ONYX_DIR%" >nul
if %ERRORLEVEL% EQU 0 (
    echo [92mOnyx is already in your PATH![0m
    echo You can use 'onyx' from anywhere.
    echo.
    pause
    exit /b 0
)

echo Current directory: %ONYX_DIR%
echo.
set /p "CONFIRM=Add to PATH? (y/n): "

if /i not "%CONFIRM%"=="y" (
    echo Setup cancelled.
    exit /b 0
)

echo.
echo Adding to User PATH...
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "CURRENT_PATH=%%b"

if "%CURRENT_PATH%"=="" (
    setx PATH "%ONYX_DIR%" >nul
) else (
    setx PATH "%CURRENT_PATH%;%ONYX_DIR%" >nul
)

echo.
echo [92mSetup Complete![0m
echo.
echo You can now use these commands from anywhere:
echo   onyx start
echo   onyx stop
echo   onyx status
echo.
echo [93mIMPORTANT: Close and reopen your terminal![0m
echo.
pause
exit /b 0
