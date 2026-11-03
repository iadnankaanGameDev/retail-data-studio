@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" "scripts\run_studio.py"
exit /b %ERRORLEVEL%
