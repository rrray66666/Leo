@echo off
chcp 65001 >nul 2>nul
title CRM System Self Check
setlocal

set "ROOT=%~dp0"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"

echo ================================================
echo    CRM System - Self Check
echo ================================================
echo.

if not exist "%VENV_PY%" (
    echo [ERROR] .venv not found. Cannot run self check.
    pause
    exit /b 1
)

echo [1/2] Python runtime:
"%VENV_PY%" --version
echo.

echo [2/2] Running checks (MySQL / backend / login / data / permissions)...
echo       Note: the backend must be running. If it is not,
echo       double-click start-all.bat first, then run this again.
echo.
"%VENV_PY%" "%ROOT%selfcheck.py"

echo.
echo Press any key to close...
pause >nul
exit /b %ERRORLEVEL%
