@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo ERROR: Install and start Docker Desktop first.
  exit /b 1
)

if not exist .env copy /Y .env.example .env >nul
docker compose --env-file .env up -d --build --wait
if errorlevel 1 exit /b 1

echo Olist Task 3 is ready.
echo API docs:   http://localhost:8000/docs
echo MLflow:     http://localhost:5000
echo MinIO:      http://localhost:9001
echo Prometheus: http://localhost:9090

