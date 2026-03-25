@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0

echo ======================================================================
echo  KOMPSAT SATELLITE DATA PROCESSOR
echo ======================================================================

REM 1. Check virtual environment
if not exist "venv\Scripts\python.exe" (
    echo [INFO] venv not found or incomplete. Creating...
    python -m venv venv
)

REM 2. Environments Check
echo [INFO] Checking environment...
venv\Scripts\python.exe -c "import osgeo; import numpy" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required libraries...
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install numpy gdal
)

REM 3. Run GUI
echo [INFO] Starting Application...
echo.

venv\Scripts\python.exe kompsat_gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application failed to start.
    pause
)

endlocal
exit /b 0
