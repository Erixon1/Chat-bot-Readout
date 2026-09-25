# Readout IA — Suite de Gestión Bibliotecaria, Préstamo de Libros y Automatización

Plataforma integral en Streamlit diseñada con arquitectura moderna, tipografía editorial y componentes visuales ejecutivos, inspirada en la temática del repositorio Readout. Cubre la totalidad de los requisitos académicos de la Tarea Académica 2 (Sesión 2 y Sesión 3):

---

## 1. Arquitectura y Módulos del Sistema

### Pestaña 0: Recepción Bibliotecaria (Flujo de Préstamo Omnicanal)
- Interacción multimodal: recepción de solicitudes de lectura por Voz (Whisper) o Texto.
- Consulta de catálogo y fichas de obras: muestra sinopsis, pilares, autores y condiciones cuando el lector consulta sobre libros.
- Protocolo de atención de la recepcionista en tres pasos:
  1. Identificación de la obra y solicitud cortés de datos de contacto (Correo electrónico y WhatsApp).
  2. Presentación del borrador estructurado de préstamo y solicitud de confirmación explícita.
  3. Despacho automatizado: registro en Google Sheets, emisión de constancia por Email (SMTP), recordatorio por WhatsApp (WAHA) y entrega del código oficial de préstamo (RO-2026-XXXX).

### Pestaña 1: BibliófiloBot (Asesor Literario y Académico - Sesión 2)
- Modelo: Chat Completions (`gpt-4o-mini` o modelos compatibles vía Groq Cloud/OpenAI) con persistencia de contexto en sesión.
- Prompt especializado en literatura universal, ingeniería de software, astrofísica, filosofía y clásicos.
- Consultas sugeridas para interacción inmediata.

### Pestaña 2: Transcriptor Whisper (Solicitudes de Lectura y Reseñas por Voz - Sesión 2)
- Modelo: `whisper-1` / `whisper-large-v3` vía Audio Transcriptions API.
- Grabación directa desde micrófono del navegador y subida de archivos de audio (`.mp3`, `.wav`, `.m4a`, `.ogg`, `.webm`).
- Audios pregrabados de prueba rápida para solicitudes de préstamo.
- Exportación de transcripciones en formato de texto (`.txt`) y reenvío automático a la Recepción.

### Pestaña 3: Gestor Readout y Automatización (OpenAI Assistants API - Sesión 3)
- Orquestación de OpenAI Assistants API (v2) por Scripting (`core/assistant.py`), sin depender del dashboard web.
- Manejo de Threads, Runs, Messages y Tool Outputs.
- Function Calling integrado:
  - `enviar_email`: Despacho real vía servidor SMTP o log local en `data/email_log.jsonl`.
  - `registrar_sheet`: Registro en Google Sheets API o espejo en `data/sheets_log.csv`.
  - `enviar_whatsapp`: Despacho vía servidor WAHA o log local en `data/whatsapp_log.jsonl`.
- Consola de disparo directo para pruebas unitarias de cada conector.

### Pestaña 4: Centro de Auditoría y Logs en Tiempo Real
- Visualización interactiva y descarga de registros históricos de préstamos (CSV).
- Historial de correos electrónicos despachados con vista de boletas.
- Registro cronológico de notificaciones de WhatsApp.

---

## 2. Requisitos Previos del Sistema

- Sistema Operativo: Windows 10/11, Linux o macOS.
- Python: Versión 3.10 o superior.
- Docker Desktop: Requerido únicamente si se desea ejecutar el servidor local de WhatsApp (WAHA).
- Credenciales opcionales para Modo Real:
  - API Key de OpenAI o Groq Cloud.
  - Cuenta de correo Gmail con Contraseña de Aplicación (para SMTP).
  - Cuenta de Servicio de Google Cloud (Service Account JSON) para Google Sheets API.
  - Servidor WAHA activo en el puerto 3000.

---

## 3. Guía de Instalación y Despliegue Paso a Paso

### Paso 1: Clonar o descargar el repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd chatbot
```

### Paso 2: Crear y activar un entorno virtual
En Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

En Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar dependencias del proyecto
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar variables de entorno
Copie el archivo de plantilla `.env.example` a `.env` de manera manual o usando PowerShell: 

En Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

En Linux / macOS:
```bash
cp .env.example .env
```

Edite el archivo `.env` con un editor de texto e ingrese las variables correspondientes según el modo deseado (Modo Real o Modo Simulación).

---

## 4. Estructura de Variables de Entorno (.env)

| Variable | Tipo | Descripción | Ejemplo |
| :--- | :--- | :--- | :--- |
| `FORCE_MOCK_MODE` | Booleano | `false` para modo real con APIs; `true` para simulación offline | `false` |
| `OPENAI_API_KEY` | Texto | Clave de API de OpenAI o Groq Cloud | `gsk_...` o `sk-proj-...` |
| `OPENAI_BASE_URL` | URL | URL base del proveedor (dejar vacío para OpenAI oficial) | `https://api.groq.com/openai/v1` |
| `OPENAI_CHAT_MODEL` | Texto | Modelo para el chat conversacional | `gpt-4o-mini` |
| `OPENAI_WHISPER_MODEL`| Texto | Modelo para transcripción de audio | `whisper-1` o `whisper-large-v3` |
| `OPENAI_ASSISTANT_MODEL`| Texto | Modelo para el Asistente con Function Calling | `gpt-4o-mini` |
| `OPENAI_ASSISTANT_ID` | Texto | Opcional. ID de asistente existente (vacío para crear por scripting) | *(vacío)* |
| `SMTP_HOST` | Host | Servidor de salida de correo | `smtp.gmail.com` |
| `SMTP_PORT` | Número | Puerto seguro de conexión SMTP | `587` |
| `SMTP_USER` | Email | Cuenta de correo remitente | `usuario@gmail.com` |
| `SMTP_PASSWORD` | Clave | Contraseña de aplicación de 16 caracteres | `abcd efgh ijkl mnop` |
| `SMTP_FROM` | Email | Dirección visible del remitente | `usuario@gmail.com` |
| `GOOGLE_SA_JSON` | Archivo | Ruta local al archivo JSON de credenciales de Google Service Account | `service_account.json` |
| `GOOGLE_SHEET_ID` | ID / URL | ID de la hoja de cálculo o enlace completo de Google Sheets | `1NUJ0LlryNtCs4L4WWf3neAXIvXowUE2VCawqCue_Dyo` |
| `WAHA_URL` | URL | Endpoint del servidor WhatsApp HTTP API (WAHA) | `http://localhost:3000` |
| `WAHA_SESSION` | Texto | Nombre de la sesión activa de WAHA | `default` |
| `WAHA_API_KEY` | Texto | Clave de seguridad del servidor WAHA (opcional) | `tu_waha_api_key` |

---

## 5. Configuración de Servicios Externos

### A. WhatsApp con WAHA (Docker)
Para habilitar notificaciones reales de WhatsApp a teléfonos de destino:
1. Iniciar el contenedor de WAHA:
```bash
docker run -d --name waha -p 3000:3000/tcp -e "WHATSAPP_HOOK_URL=http://localhost:3000/hook" devlikeapro/waha
```
2. Abrir el panel de control en `http://localhost:3000/dashboard`.
3. Iniciar la sesión `default` y escanear el código QR con WhatsApp en su dispositivo móvil.

### B. Google Sheets API
1. Crear un proyecto en Google Cloud Console y habilitar **Google Sheets API** y **Google Drive API**.
2. Crear una **Cuenta de Servicio (Service Account)** y descargar la clave en formato JSON.
3. Compartir su hoja de Google Sheets con el correo de la cuenta de servicio (`ejemplo@proyecto.iam.gserviceaccount.com`) otorgando rol de **Editor**.
4. Colocar el archivo JSON en la raíz del proyecto y especificar su nombre en `GOOGLE_SA_JSON`.

### C. Correo Electrónico SMTP (Gmail)
1. Acceder a la configuración de seguridad de su cuenta Google.
2. Activar la verificación en dos pasos.
3. Crear una **Contraseña de Aplicación** para "Correo" y utilizar dicha clave en `SMTP_PASSWORD`.

---

## 6. Ejecución de la Suite

### Opción 1: Inicio Rápido con Ejecutable (Recomendado)
Haga doble clic en el archivo **`iniciar.bat`** o ejecútelo desde la terminal:

En Windows (CMD / Doble Clic):
```cmd
iniciar.bat
```

En Windows (PowerShell):
```powershell
.\iniciar.ps1
```

Este script automatiza automáticamente:
1. La verificación y arranque del contenedor Docker de WhatsApp (WAHA) en el puerto 3000.
2. La activación del entorno virtual de Python (si existe `venv`).
3. El despliegue de la aplicación Streamlit en el puerto 8501.

### Opción 2: Ejecución Manual
```powershell
python -m streamlit run app.py
```

La plataforma se abrirá automáticamente en su navegador en:
**`http://localhost:8501`**

---

## 7. Estructura del Código Fuente

```
chatbot/
├── iniciar.bat            # Lanzador ejecutable para Windows (Doble Clic)
├── iniciar.ps1            # Script de lanzamiento para PowerShell
├── .env.example           # Plantilla de variables de entorno
├── requirements.txt       # Librerías de Python requeridas
├── app.py                 # Aplicación principal de Streamlit con interfaz visual
├── core/
│   ├── assistant.py       # OpenAI Assistants API, Threads, Runs y Function Calling
│   ├── chat.py            # Chat Completions para BibliófiloBot
│   ├── client.py          # Cliente centralizado y selector de modo real/demo
│   ├── concierge.py       # Recepcionista omnicanal, catálogo y flujo de confirmación
│   ├── demo_data.py       # Base de conocimientos y fichas detalladas de libros
│   └── transcribe.py      # Transcriptor de audio con Whisper API
├── tools/
│   ├── email_sender.py    # Conector de correo SMTP y fallback de auditoría
│   ├── sheets_logger.py   # Conector de Google Sheets API y fallback CSV
│   ├── whatsapp_sender.py # Conector de WhatsApp WAHA y fallback de auditoría
│   └── registry.py        # Esquemas Function Calling y enrutador de herramientas
├── prompts/
│   ├── assistant_instructions.md # Instrucciones del Asistente Readout
│   ├── system_biblioteca.md      # Directivas del Asesor Literario
│   └── system_concierge.md       # Protocolo formal de la Recepcionista
└── data/                  # Almacén local de auditoría y registros
    ├── email_log.jsonl    # Log histórico de boletas enviadas
    ├── sheets_log.csv     # Registro de préstamos y fianzas
    └── whatsapp_log.jsonl # Log de notificaciones de WhatsApp
```

---

## 8. Verificación y Control de Datos

- **Reiniciar Sesión:** Limpia el historial temporal en memoria manteniendo la aplicación lista para una nueva atención.
- **Limpiar Datos y Logs (0):** En la barra lateral, este botón permite reiniciar tanto la memoria de conversación como los registros persistentes en `data/`, devolviendo todos los contadores de préstamos, chats y audios a cero de forma inmediata.

---

## 9. Preguntas Frecuentes sobre Compilación y Cambios en .env (FAQ)

### ¿Se requiere ejecutar un comando de "build" al cambiar variables en el archivo .env?
**No.** Python y Streamlit leen el archivo `.env` en tiempo de ejecución (`runtime`) en cada inicio o recarga de la aplicación.
- Si modifica alguna variable o credencial en `.env`, únicamente debe reiniciar la aplicación (cerrando la ventana de terminal o ejecutando nuevamente `iniciar.bat`) o presionar el botón "Reiniciar Sesión". No existe un paso de compilación o `docker build` requerido.

### ¿Se requiere "docker build" para el servicio de WhatsApp?
**No.** El contenedor de WhatsApp (WAHA) utiliza la imagen oficial precompilada de Docker Hub (`devlikeapro/waha`). Solo se ejecuta con `docker start waha` o `docker run`, lo cual es gestionado automáticamente por `iniciar.bat`.

### ¿Cuándo se utiliza el comando de compilación (npm run build:css)?
El archivo CSS final ya viene compilado y listo para producción en `static/tailwind.css`. Únicamente si un desarrollador modifica las directivas de estilo en `src/styles/input.css` o la configuración de `tailwind.config.js`, se ejecutaría `npm run build:css` para regenerar la hoja de estilos.
