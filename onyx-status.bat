@echo off
REM Onyx Status - Check if Onyx is running
REM Windows status script

echo Checking Onyx status...
echo.

set "FOUND=0"

for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID"') do (
    for /f "tokens=*" %%b in ('wmic process where "ProcessId=%%a" get CommandLine /format:list 2^>nul ^| findstr "start_app.py"') do (
        set "FOUND=1"
        echo [92mOnyx is RUNNING[0m
        echo PID: %%a
        echo URL: http://localhost:8501
        goto :end
    )
)

:end
if "%FOUND%"=="0" (
    echo [91mOnyx is NOT running[0m
    echo.
    echo To start Onyx, run: .\onyx
)

echo.
timeout /t 2 >nul
