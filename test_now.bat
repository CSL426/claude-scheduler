@echo off
echo Testing Claude Scheduler Now
echo =============================

echo Current time: %TIME%
echo.

echo Running PowerShell script...
powershell -ExecutionPolicy Bypass -File "%~dp0claude_scheduler.ps1" -Test

echo.
echo Test completed!
echo Check the log file: scheduled_task.log
echo.

pause
