# ==============================================================================
# READOUT IA - SCRIPT DE INICIO RAPIDO (PowerShell)
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "READOUT IA - GESTION BIBLIOTECARIA Y PRESTAMO DE LIBROS" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Iniciando servicios y verificando componentes..." -ForegroundColor White
Write-Host ""

# 1. Verificar Docker / WAHA
Write-Host "[1/3] Verificando servicio de WhatsApp (WAHA en Docker)..." -ForegroundColor Yellow
try {
    $dockerCheck = docker inspect -f '{{.State.Running}}' waha 2>$null
    if ($dockerCheck -eq "true") {
        Write-Host "[OK] Contenedor WAHA ya se encuentra activo en http://localhost:3000" -ForegroundColor Green
    } else {
        Write-Host "Iniciando contenedor WAHA..." -ForegroundColor Yellow
        docker start waha | Out-Null
        if ($LASTEXITCODE -ne 0) {
            docker run -d --name waha -p 3000:3000 devlikeapro/waha | Out-Null
        }
        Write-Host "[OK] Contenedor WAHA iniciado correctamente." -ForegroundColor Green
    }
} catch {
    Write-Host "[AVISO] Docker no esta disponible. La aplicacion funcionara con logger local." -ForegroundColor DarkYellow
}
Write-Host ""

# 2. Entorno virtual
Write-Host "[2/3] Verificando entorno de Python..." -ForegroundColor Yellow
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activando entorno virtual venv..." -ForegroundColor White
    & .\venv\Scripts\Activate.ps1
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activando entorno virtual .venv..." -ForegroundColor White
    & .\.venv\Scripts\Activate.ps1
}
Write-Host "[OK] Python listo." -ForegroundColor Green
Write-Host ""

# 3. Streamlit
Write-Host "[3/3] Desplegando aplicacion Streamlit..." -ForegroundColor Yellow
Write-Host "Servidor activo en: http://localhost:8501" -ForegroundColor Cyan
Write-Host "Presione Ctrl + C para detener el servidor." -ForegroundColor Gray
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

python -m streamlit run app.py
