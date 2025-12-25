@echo off
REM Onyx Stop - Terminate Onyx server
REM Windows stop script

echo Stopping Onyx...

REM Find and kill Python processes running start_app.py
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID"') do (
    wmic process where "ProcessId=%%a and CommandLine like '%%start_app.py%%'" delete >nul 2>&1
)

echo Onyx stopped.
timeout /t 2 >nul
