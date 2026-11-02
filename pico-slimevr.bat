@echo off
setlocal EnableExtensions
chcp 65001 >nul
title pico-slimevr
cd /d "%~dp0"

rem ---------------------------------------------------------------
rem  pico-slimevr - launcher for Windows
rem  Finds Python, installs the tool once if needed, then runs it.
rem  Usage:  pico-slimevr.bat [--fix] [--dry-run] [--gui] [--explain] ...
rem ---------------------------------------------------------------

set "PY="
where py >nul 2>nul
if errorlevel 1 goto try_python
set "PY=py -3"
goto have_python

:try_python
where python >nul 2>nul
if errorlevel 1 goto no_python
set "PY=python"

:have_python
rem Run straight from the source tree if it sits next to this script.
if not exist "%~dp0src\pico_slimevr\cli.py" goto not_local
set "PYTHONPATH=%~dp0src"
%PY% -m pico_slimevr %*
set "RC=%errorlevel%"
goto finish

:not_local
rem Otherwise install the package once, then run it.
%PY% -c "import pico_slimevr" >nul 2>nul
if not errorlevel 1 goto run
echo Installing pico-slimevr (one time, needs internet)...
%PY% -m pip install --upgrade --quiet "git+https://github.com/ctenadog/pico-slimevr.git"
if errorlevel 1 goto install_failed

:run
%PY% -m pico_slimevr %*
set "RC=%errorlevel%"
goto finish

:no_python
echo.
echo [!] Python not found.
echo     Install Python 3.10+ from https://www.python.org/downloads/
echo     During setup tick "Add python.exe to PATH".
echo.
pause
exit /b 1

:install_failed
echo.
echo [!] Install failed. Check your internet connection and that Python is in PATH.
echo.
pause
exit /b 1

:finish
if "%~1"=="" pause
exit /b %RC%
