@echo off
cd /d %~dp0
set LOG=%cd%\run_gui.log
echo ===============================>>"%LOG%"
echo START %DATE% %TIME% >>"%LOG%"
echo CWD=%cd% >>"%LOG%"

echo Checking conda on PATH...>>"%LOG%"
where conda >>"%LOG%" 2>&1
if errorlevel 1 (
  echo conda not on PATH, trying common locations...>>"%LOG%"
  set "_CONDACANDS=%USERPROFILE%\miniconda3\condabin;%USERPROFILE%\anaconda3\condabin;C:\ProgramData\miniconda3\condabin;C:\ProgramData\Anaconda3\condabin"
  for %%D in (%_CONDACANDS%) do (
    if exist "%%~D\conda.bat" set "PATH=%%~D;%PATH%"
    if exist "%%~D\conda.exe" set "PATH=%%~D;%PATH%"
  )
  where conda >>"%LOG%" 2>&1
)

echo Python version in 'gis' env:>>"%LOG%"
conda run -n gis python --version >>"%LOG%" 2>&1
echo Import checks:>>"%LOG%"
conda run -n gis python -c "import tkinter, numpy; from osgeo import gdal; print('OK')" >>"%LOG%" 2>&1

echo Launching GUI...>>"%LOG%"
conda run -n gis python "%cd%\kompsat_gui.py" >>"%LOG%" 2>&1
echo GUI exit code: %ERRORLEVEL% >>"%LOG%"
echo END %DATE% %TIME% >>"%LOG%"
