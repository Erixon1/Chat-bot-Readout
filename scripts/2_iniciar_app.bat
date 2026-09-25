@echo off
cd /d "%~dp0.."
title Readout IA - Interfaz Streamlit
cls

echo ==============================================================================
echo [PASO 2] APLICACION WEB READOUT IA (STREAMLIT)
echo ==============================================================================
echo.

if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual venv...
    call venv\Scripts\activate.bat
)
if exist ".venv\Scripts\activate.bat" (
    echo Activando entorno virtual .venv...
    call .venv\Scripts\activate.bat
)

echo.
echo Iniciando servidor en http://localhost:8501...
echo.
echo Para detener unicamente la aplicacion web, presione Ctrl + C.
echo (Para apagar todos los servicios ejecute 3_detener_todo.bat)
echo ==============================================================================
echo.

python -m streamlit run app.py

pause
