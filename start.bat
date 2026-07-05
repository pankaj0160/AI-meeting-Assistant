@echo off
title Summly Dev Server

echo.
echo  Starting Summly...
echo.

cd /d C:\Projects\Summly

call .venv\Scripts\activate.bat
echo  [OK] Venv activated

cd client
if not exist node_modules npm install
cd ..
echo  [OK] Frontend ready

echo  Starting Backend...
start "Summly Backend" cmd /k "cd /d C:\Projects\Summly && call .venv\Scripts\activate.bat && uvicorn server.main:app --reload --reload-dir server --host 127.0.0.1 --port 8000"

timeout /t 4 /nobreak >nul

echo  Starting Frontend...
start "Summly Frontend" cmd /k "cd /d C:\Projects\Summly\client && npm run dev"

echo.
echo  Backend:   http://127.0.0.1:8000
echo  Frontend:  http://localhost:3000
echo  API Docs:  http://127.0.0.1:8000/docs
echo.
timeout /t 5 /nobreak >nul
start http://localhost:3000
exit