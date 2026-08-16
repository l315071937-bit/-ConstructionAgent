@echo off
chcp 65001 >nul
cd /d H:/A.AI_MODEL_DEVEL/resume/project/Achi
echo Stopping containers (data kept in Docker volumes)...
docker compose down
echo Done. Restart anytime with scripts/start_dev.bat
pause
