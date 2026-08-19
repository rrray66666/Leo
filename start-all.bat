@echo off
chcp 65001 >nul 2>nul
title CRM System Launcher
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "NODE_DIR=%ROOT%.nodejs\node-v20.19.4-win-x64"

echo ================================================
echo    CRM System - One-click start
echo    Frontend: http://localhost:5173
echo    Backend : http://127.0.0.1:8000/docs
echo ================================================
echo.

REM ---- 1. Python / venv ----
if not exist "%VENV_PY%" (
    echo [WARN] Built-in venv not found, will try system python.
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python not found. Please install Python 3.10+.
        goto :fail
    )
    set "VENV_PY=python"
)

"%VENV_PY%" -c "import fastapi, sqlalchemy, uvicorn" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Backend dependencies are missing. Install them first:
    echo         "%VENV_PY%" -m pip install -r "%BACKEND%\requirements.txt"
    goto :fail
)

REM ---- 2. Node / npm ----
set "NPM=npm"
if exist "%NODE_DIR%\npm.cmd" (
    echo [INFO] Using bundled Node.js ^(.nodejs^).
    set "PATH=%PATH%;%NODE_DIR%"
    set "NPM=%NODE_DIR%\npm.cmd"
)
where "%NPM%" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm not found. Please install Node.js 18+.
    goto :fail
)

REM ---- 3. Frontend dependencies ----
if not exist "%FRONTEND%\node_modules" (
    echo [INFO] Installing frontend dependencies ^(npm install^)...
    pushd "%FRONTEND%"
    call "%NPM%" install
    if errorlevel 1 (
        popd
        echo [ERROR] npm install failed. Please check the network.
        goto :fail
    )
    popd
)

REM ---- 4. Database connection ----
echo [INFO] Checking MySQL connection...
pushd "%BACKEND%"
"%VENV_PY%" -c "from app.database import engine; c=engine.connect(); c.close(); print('DB OK')"
set "DBRC=%ERRORLEVEL%"
popd
if not "%DBRC%"=="0" (
    echo.
    echo [ERROR] Cannot connect to MySQL. Please check:
    echo    1) MySQL service is running.
    echo    2) backend\.env  -  DATABASE_URL is correct.
    echo    3) db_init.sql has been run once ^(mysql -uroot -p ^< db_init.sql^).
    goto :fail
)

REM ---- 4.5 First run: auto create tables + load demo data ----
pushd "%BACKEND%"
"%VENV_PY%" -c "from app.database import SessionLocal; from app.models.user import User; db=SessionLocal(); has=db.query(User).first() is not None; db.close(); print('EXISTS' if has else 'EMPTY')" > "%TEMP%\crm_usercheck.txt" 2>nul
set "USERCHECK="
set /p USERCHECK=<"%TEMP%\crm_usercheck.txt"
del "%TEMP%\crm_usercheck.txt" >nul 2>nul
if /i not "%USERCHECK%"=="EXISTS" (
    echo [INFO] First run detected - creating tables and loading demo data...
    "%VENV_PY%" -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)"
    "%VENV_PY%" -m app.scripts.seed_demo
    if errorlevel 1 (
        popd
        echo [ERROR] Demo data seeding failed. See message above.
        goto :fail
    )
)
popd

REM ---- 5. Start backend ----
echo [INFO] Starting backend on http://127.0.0.1:8000 ...
start "CRM Backend" cmd /k "pushd %BACKEND% && %VENV_PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

REM ---- 6. Start frontend ----
echo [INFO] Starting frontend on http://localhost:5173 ...
start "CRM Frontend" cmd /k "pushd %FRONTEND% && call %NPM% run dev"

echo.
echo Services are starting in two new windows.
echo   Frontend : http://localhost:5173
echo   Backend  : http://127.0.0.1:8000/docs
echo First run? Seed demo data first - see README.md "Demo data".
echo.
pause
exit /b 0

:fail
echo.
echo Startup aborted. See message above.
pause
exit /b 1
