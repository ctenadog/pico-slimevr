@echo off
setlocal EnableExtensions
chcp 65001 >nul
title pico-slimevr
cd /d "%~dp0"

rem ------------------------------------------------------------------
rem  pico-slimevr - launcher for Windows
rem  Finds Python, installs the tool once if needed, then runs it.
rem  Usage:  pico-slimevr.bat [--fix] [--dry-run] [--gui] [--explain] ...
rem
rem  Deliberately no labels / no goto: those break if the file ends up
rem  with LF-only line endings. Only single-line conditionals below.
rem ------------------------------------------------------------------

set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% -c "print(1)" >nul 2>nul || (echo. & echo [!] Python not found. & echo     Install Python 3.10+ from https://www.python.org/downloads/ & echo     During setup tick "Add python.exe to PATH". & echo. & pause & exit /b 1)

set "LOCAL=1"
if not exist "%~dp0src\pico_slimevr\cli.py" set "LOCAL="
if defined LOCAL set "PYTHONPATH=%~dp0src"
if not defined LOCAL %PY% -c "import pico_slimevr" >nul 2>nul || %PY% -m pip install --upgrade --quiet "git+https://github.com/ctenadog/pico-slimevr.git"

%PY% -m pico_slimevr %*
set "RC=%errorlevel%"
if "%~1"=="" pause
exit /b %RC%
