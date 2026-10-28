@echo off
rem Starts the API (port 8000) and the web app (port 5173) in their own windows, then opens the browser.
rem Close those two windows to stop the servers.

start "Lifecycle Studio - API" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python -m uvicorn app.main:app --port 8000"
start "Lifecycle Studio - Web" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

timeout /t 6 /nobreak >nul
start "" http://localhost:5173
