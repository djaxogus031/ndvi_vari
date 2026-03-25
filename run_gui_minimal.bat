@echo off
REM Minimal launcher for KOMPSAT GUI (ASCII-only)
cd /d %~dp0

REM Ensure conda is available
where conda >nul 2>&1
if errorlevel 1 (
    set "_CONDACANDS=%USERPROFILE%\miniconda3\condabin;%USERPROFILE%\anaconda3\condabin;C:\ProgramData\miniconda3\condabin;C:\ProgramData\Anaconda3\condabin"
    for %%D in (%_CONDACANDS%) do (
        if exist "%%~D\conda.bat" set "PATH=%%~D;%PATH%"
        if exist "%%~D\conda.exe" set "PATH=%%~D;%PATH%"
    )
)

where conda >nul 2>&1
if errorlevel 1 (
    echo ERROR: conda not found. Open Anaconda Prompt and run:
    echo     conda run -n gis python "%cd%\kompsat_gui.py"
    pause
    exit /b 1
)

echo Launching GUI...
conda run -n gis python "%cd%\kompsat_gui.py"
if errorlevel 1 (
    echo ERROR: Failed to launch GUI.
    pause
    exit /b 1
)

exit /b 0
