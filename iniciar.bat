@echo off
title Readout IA - Suite de Gestion Bibliotecaria
cls

echo ==============================================================================
echo READOUT IA - GESTION BIBLIOTECARIA Y PRESTAMO DE LIBROS
echo ==============================================================================
echo Iniciando servicios y verificando componentes...
echo.

:: 1. Verificar y levantar contenedor Docker de WAHA (WhatsApp)
echo [1/3] Verificando servicio de WhatsApp (WAHA en Docker)...
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    docker inspect -f "{{.State.Running}}" waha 2>nul | findstr /i "true" >nul
    if %errorlevel% neq 0 (
        echo Iniciando contenedor waha...
        docker start waha >nul 2>&1
        if %errorlevel% neq 0 (
            echo Creando y ejecutando contenedor waha...
            docker run -d --name waha -p 3000:3000 devlikeapro/waha >nul 2>&1
        )
    )
    echo [OK] Servicio de WhatsApp WAHA listo en http://localhost:3000
) else (
    echo [AVISO] Docker no esta en ejecucion o no esta disponible. WhatsApp operara en modo local.
)
echo.

:: 2. Verificar Entorno Virtual (si existe)
echo [2/3] Verificando entorno de Python...
if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual venv...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo Activando entorno virtual .venv...
    call .venv\Scripts\activate.bat
)
echo [OK] Entorno de Python preparado.
echo.

:: 3. Iniciar aplicacion Streamlit
echo [3/3] Desplegando aplicacion web en Streamlit...
echo Servidor accesible en: http://localhost:8501
echo Para detener la aplicacion, presione Ctrl + C en esta ventana.
echo ==============================================================================
echo.

python -m streamlit run app.py

pause
