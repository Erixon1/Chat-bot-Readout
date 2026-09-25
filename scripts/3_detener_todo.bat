@echo off
cd /d "%~dp0.."
title Readout IA - Detener Servicios
cls

echo ==============================================================================
echo [PASO 3] DETENER TODOS LOS SERVICIOS (STREAMLIT Y DOCKER WAHA)
echo ==============================================================================
echo.

echo [1/2] Deteniendo contenedor Docker WAHA...
docker stop waha >nul 2>&1
if errorlevel 1 (
    echo [INFO] El contenedor WAHA ya estaba detenido o Docker no esta activo.
) else (
    echo [OK] Contenedor Docker WAHA detenido exitosamente.
)
echo.

echo [2/2] Finalizando procesos de Streamlit...
taskkill /F /IM "streamlit.exe" >nul 2>&1
echo [OK] Procesos de interfaz finalizados.
echo.
echo ==============================================================================
echo Todos los servicios de Readout IA han sido cerrados correctamente.
echo ==============================================================================
pause
