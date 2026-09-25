# ==============================================================================
# READOUT IA - [PASO 3] DETENER TODOS LOS SERVICIOS (PowerShell)
# ==============================================================================

Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "[PASO 3] DETENER TODOS LOS SERVICIOS" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Deteniendo contenedor Docker WAHA..." -ForegroundColor Yellow
$null = docker stop waha 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Contenedor WAHA detenido exitosamente." -ForegroundColor Green
} else {
    Write-Host "[INFO] El contenedor WAHA ya estaba detenido." -ForegroundColor Gray
}
Write-Host ""

Write-Host "[2/2] Finalizando procesos de Streamlit..." -ForegroundColor Yellow
Get-Process -Name "streamlit" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "[OK] Procesos de interfaz finalizados." -ForegroundColor Green
Write-Host ""

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Todos los servicios han sido detenidos correctamente." -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Cyan
