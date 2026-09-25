# ==============================================================================
# READOUT IA - [PASO 2] APLICACION STREAMLIT (PowerShell)
# ==============================================================================

Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "[PASO 2] APLICACION WEB READOUT IA (STREAMLIT)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activando entorno virtual venv..." -ForegroundColor White
    & .\venv\Scripts\Activate.ps1
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activando entorno virtual .venv..." -ForegroundColor White
    & .\.venv\Scripts\Activate.ps1
}

Write-Host ""
Write-Host "Iniciando servidor en: http://localhost:8501" -ForegroundColor Cyan
Write-Host "Para detener unicamente la aplicacion web, presione Ctrl + C." -ForegroundColor Gray
Write-Host "(Para apagar todos los servicios utilice 3_detener_todo.ps1)" -ForegroundColor DarkYellow
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

python -m streamlit run app.py
