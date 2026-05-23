@echo off
title Enterprise RAG - Launcher
setlocal enabledelayedexpansion

set ROOT=%~dp0
set BACKEND_PORT=8000
set FRONTEND_PORT=5173
set FRONTEND_URL=http://localhost:%FRONTEND_PORT%
set BACKEND_URL=http://localhost:%BACKEND_PORT%

echo ============================================
echo   Enterprise RAG Platform - Launcher
echo ============================================
echo.

:: ---------------------------------------------------------------------------
:: Prerequisites: Docker Desktop must be installed and running.
:: If docker is missing from PATH, try the common install dirs (handles the
:: case where Docker was just installed and PATH isn't refreshed yet).
:: ---------------------------------------------------------------------------
where docker >nul 2>nul
if not errorlevel 1 goto DOCKER_OK
if exist "%ProgramFiles%\Docker\Docker\resources\bin\docker.exe" set "PATH=%ProgramFiles%\Docker\Docker\resources\bin;%PATH%"
if exist "%ProgramW6432%\Docker\Docker\resources\bin\docker.exe" set "PATH=%ProgramW6432%\Docker\Docker\resources\bin;%PATH%"
if exist "%LOCALAPPDATA%\Docker\Docker\resources\bin\docker.exe" set "PATH=%LOCALAPPDATA%\Docker\Docker\resources\bin;%PATH%"
where docker >nul 2>nul
if not errorlevel 1 goto DOCKER_OK
echo [ERROR] docker not found on this machine.
echo.
echo         Install Docker Desktop:
echo           https://www.docker.com/products/docker-desktop/
echo.
echo         After install: reboot, launch Docker Desktop, wait until the tray
echo         icon says "Docker Desktop is running", then run this file again.
echo.
pause
exit /b 1
:DOCKER_OK

docker compose version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] "docker compose" v2 not available. Update Docker Desktop.
    echo.
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running. Start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------------
:: Start infrastructure (postgres, redis, qdrant, minio, ollama, neo4j).
:: Reused across launches; runs in the background.
:: ---------------------------------------------------------------------------
echo [INFO] Starting infrastructure (postgres, redis, qdrant, minio, ollama, neo4j)...
docker compose up -d postgres redis qdrant minio ollama neo4j
if errorlevel 1 (
    echo [ERROR] Failed to start infrastructure containers.
    pause
    exit /b 1
)

:: Observability stack (Prometheus + Grafana). Non-fatal if it fails to start.
echo [INFO] Starting observability (prometheus, grafana)...
docker compose up -d prometheus grafana
if errorlevel 1 (
    echo [WARN] Observability stack failed to start; continuing without it.
)

:: Wait up to ~30s for Postgres to report healthy before running migrations.
echo [INFO] Waiting for Postgres health...
set /a TRIES=0
:WAIT_PG
timeout /t 2 /nobreak >nul
docker compose ps postgres 2>nul | findstr "healthy" >nul
if not errorlevel 1 goto PG_READY
set /a TRIES+=1
if !TRIES! lss 15 goto WAIT_PG
echo [WARN] Postgres health not confirmed yet, continuing anyway...
:PG_READY

:: ---------------------------------------------------------------------------
:: Apply database migrations. First run also builds the backend image, which
:: installs the AI/ML dependencies and can take several minutes.
:: ---------------------------------------------------------------------------
echo [INFO] Applying database migrations (alembic upgrade head)...
echo        (first run builds the backend image - this can take a few minutes)
docker compose run --rm api alembic upgrade head
if errorlevel 1 (
    echo [WARN] Migrations did not complete cleanly. Check the output above.
    echo        You can retry later with: docker compose run --rm api alembic upgrade head
)

:: ---------------------------------------------------------------------------
:: Backend window: api + worker. Logs stream here; close it (X / Ctrl+C) to stop.
:: ---------------------------------------------------------------------------
echo [INFO] Starting Backend (api + worker) on port %BACKEND_PORT%...
start "RAG Backend" /d "%ROOT%" cmd /k "docker compose up api worker"

:: Wait up to ~60s for the api to answer /healthz.
echo [INFO] Waiting for backend to be ready...
set /a TRIES=0
:WAIT_API
timeout /t 3 /nobreak >nul
curl -s %BACKEND_URL%/api/v1/healthz 2>nul | findstr "ok" >nul
if not errorlevel 1 goto API_READY
set /a TRIES+=1
if !TRIES! lss 20 goto WAIT_API
echo [WARN] Backend not responding on %BACKEND_URL%/api/v1/healthz yet.
echo        Check the "RAG Backend" window for errors. Continuing...
:API_READY

:: ---------------------------------------------------------------------------
:: Frontend window: builds the SPA image (first run runs npm install + build)
:: and serves it on %FRONTEND_PORT%, proxying /api to the backend.
:: ---------------------------------------------------------------------------
echo [INFO] Starting Frontend on port %FRONTEND_PORT%...
start "RAG Frontend" /d "%ROOT%" cmd /k "docker compose up frontend"

:: Give the frontend a moment to come up, then open the browser.
echo [INFO] Waiting for frontend to come up...
timeout /t 8 /nobreak >nul
start "" "%FRONTEND_URL%"

:: ---------------------------------------------------------------------------
:: Summary
:: ---------------------------------------------------------------------------
echo.
echo ============================================
echo   ENTERPRISE RAG IS RUNNING
echo ============================================
echo   Frontend   : %FRONTEND_URL%
echo   API        : %BACKEND_URL%
echo   API docs   : %BACKEND_URL%/docs
echo   Health     : %BACKEND_URL%/api/v1/healthz
echo   Metrics    : %BACKEND_URL%/metrics
echo   Qdrant     : http://localhost:6333/dashboard
echo   Neo4j      : http://localhost:7474
echo   MinIO      : http://localhost:9001  (minioadmin / minioadmin)
echo   Prometheus : http://localhost:9090
echo   Grafana    : http://localhost:3000  (admin / admin)
echo ============================================
echo.
echo FIRST-TIME ONLY - for real chat/search answers, pull the Ollama models once:
echo   docker compose exec ollama ollama pull llama3.1:8b
echo   docker compose exec ollama ollama pull nomic-embed-text
echo.
echo Keep the "RAG Backend" and "RAG Frontend" windows open.
echo Close them (or Ctrl+C in each) to stop the app.
echo Infrastructure keeps running in the background; stop everything with:
echo   docker compose down
echo.
echo Press any key to close this launcher window.
pause >nul
endlocal
