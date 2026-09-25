@echo off
cd /d "%~dp0.."
title WAHA WhatsApp - Servicio Docker
cls

echo ==============================================================================
echo [PASO 1] SERVICIO DE WHATSAPP (WAHA - DOCKER)
echo ==============================================================================
echo.

echo Verificando Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop no esta en ejecucion.
    echo         Por favor, inicie Docker Desktop y vuelva a ejecutar este archivo.
    echo.
    pause
    exit /b
)

python core/waha_auth.py

echo.
echo [INFO] Esta ventana permanecera abierta con sus credenciales siempre visibles.
echo.
pause
