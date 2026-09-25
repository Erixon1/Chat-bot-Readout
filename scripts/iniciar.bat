@echo off
cd /d "%~dp0.."
title Readout IA - Suite de Gestion Bibliotecaria
cls

echo ==============================================================================
echo READOUT IA - GESTION BIBLIOTECARIA Y PRESTAMO DE LIBROS
echo ==============================================================================
echo.
echo Seleccione el paso o servicio que desea ejecutar:
echo.
echo  [1] Iniciar WAHA (Docker de WhatsApp con Credenciales fijas)
echo  [2] Iniciar Aplicacion Web (Streamlit en http://localhost:8501)
echo  [3] Iniciar AMBOS (Abre 2 ventanas independientes)
echo  [4] Detener todos los servicios (Streamlit y Docker WAHA)
echo  [5] Salir
echo.
echo ==============================================================================
set /p opcion="Seleccione una opcion [1-5]: "

if "%opcion%"=="1" (
    call scripts\1_iniciar_waha.bat
) else if "%opcion%"=="2" (
    call scripts\2_iniciar_app.bat
) else if "%opcion%"=="3" (
    echo Abriendo servicios en terminales independientes...
    start "WAHA - WhatsApp API" scripts\1_iniciar_waha.bat
    timeout /t 2 >nul
    start "Readout IA - Streamlit" scripts\2_iniciar_app.bat
) else if "%opcion%"=="4" (
    call scripts\3_detener_todo.bat
) else (
    exit /b
)
