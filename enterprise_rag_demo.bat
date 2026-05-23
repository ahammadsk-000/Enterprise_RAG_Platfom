@echo off
title Enterprise RAG - DEMO MODE
setlocal enabledelayedexpansion

set ROOT=%~dp0
set BACKEND_DIR=%ROOT%backend
set FRONTEND_DIR=%ROOT%frontend
set VENV=%BACKEND_DIR%\.venv
set PY=%VENV%\Scripts\python.exe
set BACKEND_PORT=8000
set FRONTEND_PORT=5173
set FRONTEND_URL=http://localhost:%FRONTEND_PORT%
set BACKEND_URL=http://localhost:%BACKEND_PORT%

:: ---------------------------------------------------------------------------
:: DEMO MODE config: fake LLM/embeddings, in-memory vector/graph/storage,
:: inline ingestion (no Celery worker/broker, no Ollama, no Qdrant/MinIO/Neo4j).
:: Only a tiny Postgres container is needed. These env vars are inherited by the
:: backend window launched below.
:: ---------------------------------------------------------------------------
set ENVIRONMENT=test
set INGESTION_INLINE=true
set DEBUG=true
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set POSTGRES_USER=rag
set POSTGRES_PASSWORD=rag
set POSTGRES_DB=enterprise_rag
set AUTH_SECRET_KEY=demo-only-secret-key-change-me-please-0123456789

echo ============================================
echo   Enterprise RAG Platform - DEMO MODE
echo ============================================
echo   Lightweight: native Python + Postgres container only.
echo   Fake LLM/embeddings, in-memory vector/graph. Upload .txt/.md/.html files.
echo.

:: --- Tool checks ---------------------------------------------------------
where python >nul 2>nul || (echo [ERROR] Python not found on PATH. Install Python 3.12+ ^& retry. & pause & exit /b 1)
where node   >nul 2>nul || (echo [ERROR] Node.js not found on PATH. Install Node 20+ ^& retry. & pause & exit /b 1)

:: --- Postgres (single lightweight container) -----------------------------
where docker >nul 2>nul
if not errorlevel 1 goto DOCKER_OK
if exist "%ProgramFiles%\Docker\Docker\resources\bin\docker.exe" set "PATH=%ProgramFiles%\Docker\Docker\resources\bin;%PATH%"
if exist "%LOCALAPPDATA%\Docker\Docker\resources\bin\docker.exe" set "PATH=%LOCALAPPDATA%\Docker\Docker\resources\bin;%PATH%"
where docker >nul 2>nul
if not errorlevel 1 goto DOCKER_OK
echo [ERROR] docker not found. Demo needs Docker only to run a small Postgres container.
echo         Install Docker Desktop, start it, then run this file again.
pause
exit /b 1
:DOCKER_OK

docker info >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running. Start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [INFO] Starting Postgres container...
pushd "%ROOT%"
docker compose up -d postgres
popd
if errorlevel 1 (echo [ERROR] Failed to start Postgres. & pause & exit /b 1)

echo [INFO] Waiting for Postgres health...
set /a TRIES=0
:WAIT_PG
timeout /t 2 /nobreak >nul
docker compose -f "%ROOT%docker-compose.yml" ps postgres 2>nul | findstr "healthy" >nul
if not errorlevel 1 goto PG_READY
set /a TRIES+=1
if !TRIES! lss 15 goto WAIT_PG
echo [WARN] Postgres health not confirmed; continuing anyway...
:PG_READY

:: --- Python venv + lightweight deps --------------------------------------
if not exist "%PY%" (
    echo [INFO] Creating Python virtual env ^(first run^)...
    python -m venv "%VENV%"
    echo [INFO] Installing demo dependencies ^(lightweight^)...
    "%PY%" -m pip install --quiet --upgrade pip
    "%PY%" -m pip install --quiet -r "%BACKEND_DIR%\requirements-demo.txt"
    if errorlevel 1 (echo [ERROR] pip install failed. & pause & exit /b 1)
) else (
    echo [INFO] Reusing existing venv at backend\.venv ^(delete it to reinstall^).
)

:: --- Database migrations --------------------------------------------------
echo [INFO] Applying database migrations...
pushd "%BACKEND_DIR%"
"%VENV%\Scripts\alembic.exe" upgrade head
if errorlevel 1 (echo [WARN] Migrations did not complete cleanly; check output above.)
popd

:: --- Backend (native uvicorn, demo env) ----------------------------------
echo [INFO] Starting Backend on %BACKEND_URL% ...
start "RAG Backend (demo)" /d "%BACKEND_DIR%" cmd /k ^
  "set ENVIRONMENT=test&& set INGESTION_INLINE=true&& set DEBUG=true&& set POSTGRES_HOST=localhost&& set POSTGRES_USER=rag&& set POSTGRES_PASSWORD=rag&& set POSTGRES_DB=enterprise_rag&& set AUTH_SECRET_KEY=demo-only-secret-key-change-me-please-0123456789&& "%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT%"

echo [INFO] Waiting for backend to be ready...
set /a TRIES=0
:WAIT_API
timeout /t 3 /nobreak >nul
curl -s %BACKEND_URL%/api/v1/healthz 2>nul | findstr "ok" >nul
if not errorlevel 1 goto API_READY
set /a TRIES+=1
if !TRIES! lss 20 goto WAIT_API
echo [WARN] Backend not responding yet; check the "RAG Backend (demo)" window.
:API_READY

:: --- Frontend (native Vite dev server) -----------------------------------
if not exist "%FRONTEND_DIR%\node_modules" (
    echo [INFO] Installing frontend dependencies ^(first run^)...
    pushd "%FRONTEND_DIR%"
    call npm install
    popd
)
echo [INFO] Starting Frontend on %FRONTEND_URL% ...
start "RAG Frontend (demo)" /d "%FRONTEND_DIR%" cmd /k "npm run dev"

echo [INFO] Waiting for frontend to compile...
timeout /t 6 /nobreak >nul
start "" "%FRONTEND_URL%"

echo.
echo ============================================
echo   ENTERPRISE RAG (DEMO) IS RUNNING
echo ============================================
echo   Frontend  : %FRONTEND_URL%
echo   API       : %BACKEND_URL%
echo   API docs  : %BACKEND_URL%/docs
echo   Health    : %BACKEND_URL%/api/v1/healthz
echo ============================================
echo.
echo Try it: Register an org ^> upload a .txt/.md file ^> Search ^> Chat.
echo Answers come from a deterministic FAKE LLM (no GPU/model needed); retrieval
echo  (hybrid dense+BM25), chunking, citations, graph and agents are all real.
echo.
echo Note: vector/graph/file stores are in-memory, so a backend restart needs a
echo  delete the docs and re-upload (Reindex cannot recover after a full restart). Postgres data persists.
echo.
echo Keep both windows open. Stop Postgres later with:  docker compose down
echo Press any key to close this launcher window.
pause >nul
endlocal
