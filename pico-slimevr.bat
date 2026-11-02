@echo off
setlocal EnableExtensions
chcp 65001 >nul
title pico-slimevr
cd /d "%~dp0"

rem ------------------------------------------------------------------
rem  pico-slimevr - launcher for Windows.  No Python required.
rem
rem  Downloads the ready-made pico-slimevr.exe once and runs it.
rem  Bump STAMP whenever a new build must replace an older exe.
rem  Usage:  pico-slimevr.bat [--fix] [--dry-run] [--gui] [--explain] ...
rem
rem  Deliberately no labels / no goto: those break if the file ends up
rem  with LF-only line endings. Only single-line conditionals below.
rem ------------------------------------------------------------------

set "STAMP=2026-11-02b"
set "EXE=%~dp0pico-slimevr.exe"
set "STAMPFILE=%~dp0pico-slimevr.stamp"
set "URL=https://github.com/ctenadog/pico-slimevr/releases/latest/download/pico-slimevr.exe"

set "OLD="
set "NEED=1"
if exist "%EXE%" if exist "%STAMPFILE%" set /p OLD=<"%STAMPFILE%"
if exist "%EXE%" if exist "%STAMPFILE%" if "%OLD%"=="%STAMP%" set "NEED="

if defined NEED echo Downloading pico-slimevr.exe (one time, needs internet)...
if defined NEED powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%URL%' -OutFile '%EXE%' -UseBasicParsing } catch { exit 1 }"
if defined NEED if not exist "%EXE%" curl -fsSL "%URL%" -o "%EXE%"
if defined NEED if exist "%EXE%" echo %STAMP%>"%STAMPFILE%"

if exist "%EXE%" "%EXE%" %*
if exist "%EXE%" set "RC=%errorlevel%"
if exist "%EXE%" if "%~1"=="" pause
if exist "%EXE%" exit /b %RC%

rem --- Download failed: fall back to Python, if it happens to be installed ---
echo.
echo [!] Could not download pico-slimevr.exe.
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% -c "print(1)" >nul 2>nul || (echo     Check your internet connection, then run this file again. & echo. & pause & exit /b 1)
echo     Falling back to Python...
set "LOCAL=1"
if not exist "%~dp0src\pico_slimevr\cli.py" set "LOCAL="
if defined LOCAL set "PYTHONPATH=%~dp0src"
if not defined LOCAL %PY% -c "import pico_slimevr" >nul 2>nul || %PY% -m pip install --upgrade --quiet "git+https://github.com/ctenadog/pico-slimevr.git"
%PY% -m pico_slimevr %*
set "RC=%errorlevel%"
if "%~1"=="" pause
exit /b %RC%
