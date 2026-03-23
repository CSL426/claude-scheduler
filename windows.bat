@echo off
echo Claude Auto Reset Task Setup Tool
echo ================================

echo Checking administrator privileges...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges.
) else (
    echo ERROR: Administrator privileges required!
    echo Please right-click on this batch file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Setting PowerShell execution policy...
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force"

echo.
echo Setting up Windows Task Scheduler...
echo Will create the following scheduled tasks:
echo - Claude_0730 (daily at 07:30)
echo - Claude_1230 (daily at 12:30)
echo - Claude_1730 (daily at 17:30)
echo - Claude_2230 (daily at 22:30)
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0claude_scheduler.ps1" -Setup

echo.
echo Setup completed!
echo.
echo Script will automatically execute 'claude -p hi' at:
echo - Daily 07:30 (start of workday)
echo - Daily 12:30 (midday)
echo - Daily 17:30 (afternoon)
echo - Daily 22:30 (evening)
echo.
echo This matches Claude's 5-hour reset cycle
echo Log file: scheduled_task.log
echo.
pause
