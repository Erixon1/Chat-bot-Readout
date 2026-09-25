# ==============================================================================
# READOUT IA - LANZADOR PRINCIPAL (PowerShell)
# ==============================================================================

Set-Location (Join-Path $PSScriptRoot "..")
Clear-Host

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "READOUT IA - GESTION BIBLIOTECARIA Y PRESTAMO DE LIBROS" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Seleccione el paso o servicio que desea ejecutar:" -ForegroundColor White
Write-Host ""
Write-Host "  [1] Iniciar WAHA (Docker WhatsApp y Credenciales en pantalla)" -ForegroundColor Yellow
Write-Host "  [2] Iniciar Aplicacion Web (Streamlit en http://localhost:8501)" -ForegroundColor Green
Write-Host "  [3] Iniciar AMBOS (Abre 2 ventanas independientes)" -ForegroundColor Magenta
Write-Host "  [4] Detener todos los servicios (Streamlit y Docker WAHA)" -ForegroundColor Red
Write-Host "  [5] Salir" -ForegroundColor Gray
Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan

$opcion = Read-Host "Seleccione una opcion [1-5]"

switch ($opcion) {
    "1" {
        & .\scripts\1_iniciar_waha.ps1
    }
    "2" {
        & .\scripts\2_iniciar_app.ps1
    }
    "3" {
        Start-Process powershell -ArgumentList "-NoExit", "-File", ".\scripts\1_iniciar_waha.ps1"
        Start-Sleep -Seconds 2
        Start-Process powershell -ArgumentList "-NoExit", "-File", ".\scripts\2_iniciar_app.ps1"
    }
    "4" {
        & .\scripts\3_detener_todo.ps1
    }
    default {
        Write-Host "Operacion cancelada." -ForegroundColor Gray
    }
}
