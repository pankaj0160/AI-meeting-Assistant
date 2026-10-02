@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run the setup steps first.
  pause
  exit /b 1
)
if not exist ".env" (
  echo [ERROR] .env not found. Create it first.
  pause
  exit /b 1
)

echo Starting Summly...
start "Summly Backend" powershell -NoExit -ExecutionPolicy Bypass -Command ".\.venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000"
start "Summly Worker" powershell -NoExit -ExecutionPolicy Bypass -Command ".\.venv\Scripts\python.exe -m celery -A server.core.tasks.celery_app worker --loglevel=info --pool=solo"
start "Summly Frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "cd client; npm run dev"

echo Waiting for servers to come up...
timeout /t 20 /nobreak >nul
start http://localhost:3000
echo Summly is starting. Close the 3 windows to stop it.
