@echo off
where claude-scheduler >nul 2>&1
if errorlevel 1 goto not_installed
claude-scheduler install
exit /b %errorlevel%

:not_installed
echo claude-scheduler is not installed. 1>&2
echo Run: python -m pip install --editable "%~dp0" 1>&2
exit /b 1
