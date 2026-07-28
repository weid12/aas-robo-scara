# ==============================================================
#  start.ps1 — Inicializa backend, frontend e cliente OPC UA
# ==============================================================

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR = Join-Path $ROOT "web\backend"
$BACKEND_PYTHON = Join-Path $BACKEND_DIR ".venv\Scripts\python.exe"
$FRONTEND_DIR = Join-Path $ROOT "web\frontend"
$CLIENT_DIR = Join-Path $ROOT "acquisition\client"
$CLIENT_PYTHON = Join-Path $ROOT ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  AAS Robo SCARA -- Startup"                        -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# ── Backend ──────────────────────────────────────────────────
Write-Host "[1/3] Iniciando Backend em http://localhost:5000 ..." -ForegroundColor Yellow
$backendCmd = "Set-Location '$BACKEND_DIR'; Write-Host 'Backend iniciado em http://localhost:5000' -ForegroundColor Green; & '$BACKEND_PYTHON' app.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 1

# ── Frontend ─────────────────────────────────────────────────
Write-Host "[2/3] Iniciando Frontend em http://localhost:5173 ..." -ForegroundColor Yellow
$frontendCmd = "Set-Location '$FRONTEND_DIR'; Write-Host 'Frontend iniciado em http://localhost:5173' -ForegroundColor Green; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Start-Sleep -Seconds 1

# ── OPC UA Client ────────────────────────────────────────────
Write-Host "[3/3] Iniciando OPC UA Client ..." -ForegroundColor Yellow
$clientCmd = "Set-Location '$CLIENT_DIR'; Write-Host 'OPC UA Client iniciado' -ForegroundColor Green; & '$CLIENT_PYTHON' client_asyncua.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $clientCmd

Write-Host ""
Write-Host "  Backend        --> http://localhost:5000" -ForegroundColor Green
Write-Host "  Frontend       --> http://localhost:5173" -ForegroundColor Green
Write-Host "  OPC UA Client  --> Rodando em segundo plano" -ForegroundColor Green
Write-Host ""
Write-Host "  Feche as janelas abertas para encerrar os servidores." -ForegroundColor Gray
Write-Host ""
