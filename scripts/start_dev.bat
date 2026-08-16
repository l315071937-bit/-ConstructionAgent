@echo off
chcp 65001 >nul
cd /d H:/A.AI_MODEL_DEVEL/resume/project/Achi

echo ============================================
echo  ConstructionAgent one-click start
echo ============================================

echo [1/4] Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo   Docker not running, starting Docker Desktop...
    start "" "C:/Program Files/Docker/Docker/Docker Desktop.exe"
    timeout /t 60 /nobreak >nul
    docker info >nul 2>&1
    if errorlevel 1 (
        echo   Docker still not ready. Start Docker Desktop manually, then re-run.
        pause
        exit /b 1
    )
)
echo   Docker OK

echo [2/4] Starting containers (PostgreSQL / Redis / Milvus)...
docker compose up -d
if errorlevel 1 (
    echo   docker compose failed, check Docker Desktop.
    pause
    exit /b 1
)

echo [3/4] Waiting 15s for health...
timeout /t 15 /nobreak >nul

echo [4/4] Starting backend and frontend in new windows...
start "ConstructionAgent-Backend" cmd /k "cd /d H:/A.AI_MODEL_DEVEL/resume/project/Achi/backend && ..\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000"
start "ConstructionAgent-Frontend" cmd /k "cd /d H:/A.AI_MODEL_DEVEL/resume/project/Achi/frontend && npm run dev"

echo.
echo  All started!
echo  Browser:  http://localhost:5173
echo  Login:    admin / admin123
echo  NOTE: first question after startup is slow (~90s, BGE-M3 loading)
echo  Keep the two windows open. To stop: scripts/stop_dev.bat
pause
