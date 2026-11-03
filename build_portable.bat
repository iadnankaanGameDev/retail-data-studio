@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Build requires a Python 3.12 development environment. Customers do not need Python.
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" scripts\make_app_icon.py
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm RetailDataStudio.spec
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" scripts\finalize_portable.py
if errorlevel 1 exit /b 1
echo Portable folder: %CD%\dist\RetailDataStudio
echo Distribute the entire folder, not just the EXE. DeliveryProbe.exe is QA only.
