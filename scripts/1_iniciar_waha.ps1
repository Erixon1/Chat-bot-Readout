# ==============================================================================
# READOUT IA - [PASO 1] SERVICIO DE WHATSAPP WAHA (PowerShell)
# ==============================================================================

Set-Location (Join-Path $PSScriptRoot "..")
Clear-Host

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "[PASO 1] SERVICIO DE WHATSAPP (WAHA - DOCKER)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$dockerRunning = $false
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Write-Host "[ERROR] Docker Desktop no esta en ejecucion." -ForegroundColor Red
    Write-Host "        Por favor inicie Docker Desktop y vuelva a ejecutar este script." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Presione Enter para salir"
    exit
}

python core/waha_auth.py

Write-Host ""
Write-Host "[INFO] Esta ventana permanecera abierta con sus credenciales siempre visibles." -ForegroundColor Green
Write-Host ""
Read-Host "Presione Enter cuando desee cerrar esta ventana (el contenedor seguira activo)"
