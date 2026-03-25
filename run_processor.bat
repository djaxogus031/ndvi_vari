@echo off
setlocal
cd /d %~dp0

echo ======================================================================
echo  KOMPSAT Batch Processor
echo ======================================================================
echo.

if not exist "venv" (
    echo [INFO] venv not found. Creating...
    python -m venv venv
)

echo.
echo Searching for L3A_* folders...
set FOUND=0
for /d %%D in (L3A_*) do (
    set FOUND=1
    echo Processing folder: %%D
    echo.
    echo Starting...
    
    venv\Scripts\python.exe kompsat_auto_processor.py "%%D"
    
    if errorlevel 1 (
        echo.
        echo [ERROR] Problem during processing.
        pause
        exit /b 1
    )
    
    echo.
    echo ======================================================================
    echo  COMPLETED!
    echo ======================================================================
    echo Result location: %%D\ProcessedOutputs
    echo.
)

if %FOUND%==0 (
    echo [WARNING] No folders starting with L3A_ found.
    echo.
    echo Manual run example:
    echo   venv\Scripts\python.exe kompsat_auto_processor.py "FOLDER_PATH"
    echo.
)

pause
endlocal
