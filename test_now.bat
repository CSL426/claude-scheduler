@echo off
where ccs >nul 2>&1
if errorlevel 1 goto python_fallback
ccs run
exit /b %errorlevel%

:python_fallback
pushd "%~dp0"
python -m claude_scheduler run
set "scheduler_exit=%errorlevel%"
popd
exit /b %scheduler_exit%
