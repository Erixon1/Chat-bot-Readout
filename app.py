import base64
import csv
import html
import json
import math
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

from core.client import is_demo_mode, CHAT_MODEL, WHISPER_MODEL, ASSISTANT_MODEL, get_api_key, get_base_url
from core.chat import chat_reply
from core.transcribe import transcribe_audio
from core.assistant import chat_with_assistant
from core.concierge import chat_with_concierge
from tools.email_sender import send_email
from tools.sheets_logger import log_to_sheet
from tools.whatsapp_sender import send_whatsapp

# Configuración de página
st.set_page_config(
    page_title="Readout IA · Gestión Bibliotecaria",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper para renderizar HTML sin que markdown-it active bloques de código
def render_html(html_str: str) -> None:
    cleaned = re.sub(r'^[ \t]+', '', html_str.strip(), flags=re.MULTILINE)
    st.markdown(cleaned, unsafe_allow_html=True)

esc = html.escape

def esc_block(text: str) -> str:
    """Escapa texto multilínea para <pre>: los saltos reales cortarían el bloque HTML de markdown."""
    return esc(text).replace("\n", "&#10;")

# ---------- GESTIÓN DE ESTADO GLOBAL ----------
for k, v in {
    "concierge_msgs": [],
    "chat_msgs": [],
    "asist_msgs": [],
    "thread_id": None,
    "transcripciones": [],
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

DEMO = is_demo_mode()

# ---------- CARGA DE TAILWIND CSS COMPILADO + FUENTES ----------
TAILWIND_CSS_PATH = Path(__file__).resolve().parent / "static" / "tailwind.css"
tailwind_css = ""
if TAILWIND_CSS_PATH.exists():
    tailwind_css = TAILWIND_CSS_PATH.read_text(encoding="utf-8")

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=Montserrat:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# Logos sin fondo embebidos como data URI (Streamlit no sirve /static sin configuración extra)
STATIC_DIR = Path(__file__).resolve().parent / "static"

def png_data_uri(name: str) -> str:
    p = STATIC_DIR / name
    return ("data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()) if p.exists() else ""

LOGO_SRC = png_data_uri("logo.png")      # "R" + "ReadOut"
LOGO_R_SRC = png_data_uri("logo-r.png")  # solo la "R"

def logo_html(css_class: str) -> str:
    return f'<img class="{css_class}" src="{LOGO_SRC}" alt="ReadOut">' if LOGO_SRC else '<span class="rd-wordmark">ReadOut</span>'

if tailwind_css:
    st.markdown(f"<style>\n{tailwind_css}\n</style>", unsafe_allow_html=True)


# ---------- MOTIVOS GRÁFICOS (SVG GENERADO) ----------
BLUE = "#2E5BFF"

def sunburst_svg(size: int = 200, rays: int = 44) -> str:
    """Estallido de rayos con largos variables (motivo del reloj del transcriptor)."""
    c = size / 2
    lines = []
    for i in range(rays):
        a = 2 * math.pi * i / rays
        r1 = size * 0.1
        r2 = size * (0.3 + 0.18 * ((i * 7) % 5) / 4)
        lines.append(
            f'<line x1="{c + r1 * math.cos(a):.1f}" y1="{c + r1 * math.sin(a):.1f}" '
            f'x2="{c + r2 * math.cos(a):.1f}" y2="{c + r2 * math.sin(a):.1f}" />'
        )
    return (f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" fill="none" stroke="{BLUE}" '
            f'stroke-width="{size * 0.022:.1f}" stroke-linecap="round" aria-hidden="true">{"".join(lines)}</svg>')


def get_system_health():
    """Diagnóstico en tiempo real del Proveedor de IA, Modelos activos y Conectores de Tools."""
    base_url = get_base_url()
    demo_mode = is_demo_mode()

    if "groq.com" in (base_url or "").lower():
        provider_name = "Groq Cloud"
    elif "openrouter.ai" in (base_url or "").lower():
        provider_name = "OpenRouter"
    elif base_url:
        provider_name = "OpenAI Compatible"
    else:
        provider_name = "OpenAI Oficial"

    ai_connected = not demo_mode

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pwd = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_port = os.getenv("SMTP_PORT", "587").strip()
    smtp_ok = bool(smtp_host and smtp_user and smtp_pwd)

    sa_json = os.getenv("GOOGLE_SA_JSON", "").strip()
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    sa_exists = Path(sa_json).exists() if sa_json else False
    sheets_ok = bool(sa_exists and sheet_id)

    waha_url = os.getenv("WAHA_URL", "").strip().rstrip("/")
    waha_key = os.getenv("WAHA_API_KEY", "").strip()
    waha_ok = False
    waha_detail = "Simulado en local (data/)"
    if waha_url:
        try:
            import requests
            headers = {"X-Api-Key": waha_key} if waha_key else {}
            r = requests.get(f"{waha_url}/api/sessions", headers=headers, timeout=1.2)
            if r.status_code in (200, 201):
                waha_ok = True
                waha_detail = f"Servidor WAHA activo ({waha_url})"
            elif r.status_code == 401:
                waha_ok = True
                waha_detail = "Servidor WAHA activo (requiere autenticación)"
            else:
                waha_detail = f"WAHA respondió HTTP {r.status_code}"
        except Exception:
            waha_detail = f"WAHA inaccesible en {waha_url}"

    tools_count = sum([1 for ok in [smtp_ok, sheets_ok, waha_ok] if ok])

    return {
        "ai_connected": ai_connected,
        "provider_name": provider_name,
        "chat_model": CHAT_MODEL,
        "whisper_model": WHISPER_MODEL,
        "assistant_model": ASSISTANT_MODEL,
        "demo": demo_mode,
        "smtp": {
            "connected": smtp_ok,
            "detail": f"{smtp_host}:{smtp_port}" if smtp_ok else "Simulado en data/email_log.jsonl"
        },
        "sheets": {
            "connected": sheets_ok,
            "detail": f"Hoja {sheet_id[:14]}…" if sheets_ok else "Simulado en data/sheets_log.csv"
        },
        "waha": {
            "connected": waha_ok,
            "detail": waha_detail
        },
        "tools_count": tools_count,
    }


def get_system_metrics():
    data_dir = Path("data")
    email_count = 0
    sheet_count = 0
    wsp_count = 0

    if (data_dir / "email_log.jsonl").exists():
        email_count = len([l for l in (data_dir / "email_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()])
    if (data_dir / "sheets_log.csv").exists():
        lines = [l for l in (data_dir / "sheets_log.csv").read_text(encoding="utf-8").splitlines() if l.strip()]
        sheet_count = max(0, len(lines) - 1)
    if (data_dir / "whatsapp_log.jsonl").exists():
        wsp_count = len([l for l in (data_dir / "whatsapp_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()])

    chat_total = len(st.session_state.concierge_msgs) + len(st.session_state.chat_msgs) + len(st.session_state.asist_msgs)
    audio_total = len(st.session_state.transcripciones)

    return {
        "chat_total": chat_total,
        "audio_total": audio_total,
        "auto_total": sheet_count,
        "email_total": email_count,
        "wsp_total": wsp_count
    }

metrics = get_system_metrics()
health = get_system_health()

MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
now = datetime.now()
fecha_hoy = f"{now.day:02d} {MESES[now.month - 1]} {now.year}"


def dot(on: bool) -> str:
    return f'<span class="rd-dot{"" if on else " rd-dot--off"}"></span>'


def section_head(num: str, label: str, title_html: str, caption: str) -> None:
    render_html(f"""
    <div class="rd-section-head">
      <div>
        <span class="rd-eyebrow"><b>{num}</b> &nbsp;/&nbsp; {label}</span>
        <h2 class="rd-display rd-h2">{title_html}</h2>
      </div>
      <p class="rd-section-cap">{caption}</p>
    </div>
    """)


def render_actions(actions: list[str]) -> None:
    """Lista de acciones ejecutadas por las herramientas: '[herramienta] detalle'."""
    items = []
    for act in actions:
        m = re.match(r'^\[([^\]]+)\]\s*(.*)$', act, flags=re.S)
        tool, detail = (m.group(1), m.group(2)) if m else ("acción", act)
        items.append(f"<li><code>{esc(tool)}</code><span>{esc(detail)}</span></li>")
    render_html(f"""
    <div class="rd-actions">
      <span class="rd-label">Acciones ejecutadas</span>
      <ul>{"".join(items)}</ul>
    </div>
    """)


# ---------- BARRA SUPERIOR ----------
ai_status = (f'{dot(True)} {esc(health["provider_name"])} conectado' if health["ai_connected"]
             else '<span class="rd-dot rd-dot--warn"></span> Modo simulación')
render_html(f"""
<div class="rd-topbar">
  <span class="rd-status">{ai_status}</span>
</div>
""")

# ---------- PORTADA ----------
render_html(f"""
<section class="rd-hero">
  <div class="rd-hero-meta">
    <span>{fecha_hoy}</span>
    <span>Biblioteca Readout · Asistente de préstamos</span>
  </div>
  <div class="rd-hero-grid">
    <div>
      <h1 class="rd-display rd-hero-title">Biblioteca<br>Readout IA</h1>
      <p class="rd-hero-lead">Préstamos, asesoría literaria y transcripción de voz, atendidos por un asistente que registra cada operación y avisa al lector por correo y WhatsApp.</p>
      <div class="rd-hero-models">
        <span>chat <b>{esc(health['chat_model'])}</b></span>
        <span>voz <b>{esc(health['whisper_model'])}</b></span>
        <span>gestor <b>{esc(health['assistant_model'])}</b></span>
      </div>
    </div>
    <div class="rd-hero-art">{f'<img src="{LOGO_R_SRC}" alt="">' if LOGO_R_SRC else ''}</div>
  </div>
</section>
""")

# ---------- FRANJA DE INTEGRACIONES ----------
stack = [
    (health["provider_name"], health["ai_connected"]),
    ("Whisper", health["ai_connected"]),
    ("Gmail SMTP", health["smtp"]["connected"]),
    ("Google Sheets", health["sheets"]["connected"]),
    ("WAHA", health["waha"]["connected"]),
]
render_html(
    '<div class="rd-stack">'
    + "".join(f'<span class="rd-stack-item">{dot(on)}{esc(name)}</span>' for name, on in stack)
    + '</div>'
)

# ---------- BENTO DE MÉTRICAS ----------
checklist = "".join(
    f'<li class="{"is-on" if on else ""}"><span>{name}</span><span>{"activo" if on else "simulado"}</span></li>'
    for name, on in [("Email", health["smtp"]["connected"]),
                     ("Google Sheets", health["sheets"]["connected"]),
                     ("WhatsApp", health["waha"]["connected"])]
)
render_html(f"""
<div class="rd-bento">
  <div class="rd-tile rd-tile--blue">
    <p class="rd-tile-label">Préstamos registrados</p>
    <p class="rd-tile-num">{metrics['auto_total']:02d}</p>
    <p class="rd-tile-foot">Filas acumuladas en la hoja de Readout</p>
  </div>
  <div class="rd-tile rd-tile--dark">
    <div class="rd-mini-grid">
      <div><span>Mensajes</span><strong>{metrics['chat_total']}</strong></div>
      <div><span>Audios</span><strong>{metrics['audio_total']}</strong></div>
      <div><span>Correos</span><strong>{metrics['email_total']}</strong></div>
      <div><span>WhatsApp</span><strong>{metrics['wsp_total']}</strong></div>
    </div>
  </div>
  <div class="rd-tile rd-tile--paper">
    <div>
      <p class="rd-tile-label">Integraciones</p>
      <ul class="rd-checklist">{checklist}</ul>
    </div>
    <p class="rd-tile-num" style="font-size:2.4rem;">{health['tools_count']}/3</p>
  </div>
</div>
""")

# ---------- BARRA LATERAL (SIDEBAR) ----------
with st.sidebar:
    render_html(f"""
    <div class="rd-side-brand">
      {logo_html("rd-logo rd-logo--side")}
      <p>Gestión bibliotecaria asistida</p>
    </div>
    """)

    render_html(f"""
    <p class="rd-label">Modelos</p>
    <dl class="rd-dl">
      <div><dt>Proveedor</dt><dd class="rd-conn">{dot(health['ai_connected']) if health['ai_connected'] else '<span class="rd-dot rd-dot--warn"></span>'}{esc(health['provider_name']) if health['ai_connected'] else 'Simulación local'}</dd></div>
      <div><dt>Chat</dt><dd class="rd-mono">{esc(health['chat_model'])}</dd></div>
      <div><dt>Voz</dt><dd class="rd-mono">{esc(health['whisper_model'])}</dd></div>
      <div><dt>Gestor</dt><dd class="rd-mono">{esc(health['assistant_model'])}</dd></div>
    </dl>
    """)

    conn_rows = "".join(
        f'<div><dt>{label}</dt><dd><span class="rd-conn">{dot(info["connected"])}{"Conectado" if info["connected"] else "Desconectado"}</span><small>{esc(info["detail"])}</small></dd></div>'
        for label, info in [("Email", health["smtp"]), ("Sheets", health["sheets"]), ("WhatsApp", health["waha"])]
    )
    render_html(f"""
    <p class="rd-label">Integraciones</p>
    <dl class="rd-dl">{conn_rows}</dl>
    """)

    if st.button("Verificar conexión", key="btn_test_tools", width="stretch"):
        st.rerun()

    if st.button("Reiniciar sesión", width="stretch"):
        st.session_state.concierge_msgs = []
        st.session_state.chat_msgs = []
        st.session_state.asist_msgs = []
        st.session_state.thread_id = None
        st.session_state.transcripciones = []
        st.success("Sesión reiniciada con éxito.")
        st.rerun()

    if st.button("Limpiar datos y logs", width="stretch"):
        st.session_state.concierge_msgs = []
        st.session_state.chat_msgs = []
        st.session_state.asist_msgs = []
        st.session_state.thread_id = None
        st.session_state.transcripciones = []
        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "sheets_log.csv").write_text("fecha_utc,tipo,detalle,monto,fecha_ref,destino\n", encoding="utf-8")
        (data_dir / "email_log.jsonl").write_text("", encoding="utf-8")
        (data_dir / "whatsapp_log.jsonl").write_text("", encoding="utf-8")
        st.success("Historial de chats, audios y logs de préstamos reseteados a 0.")
        st.rerun()

# ---------- PESTAÑAS PRINCIPALES ----------
tab_omni, tab_chat, tab_audio, tab_asist, tab_logs = st.tabs([
    "01 Recepción",
    "02 Asesor literario",
    "03 Transcriptor",
    "04 Gestor",
    "05 Auditoría"
])

def process_concierge_message(user_text: str) -> None:
    st.session_state.concierge_msgs.append({"role": "user", "content": user_text})
    with st.spinner("La Recepción de Readout está procesando su solicitud, verificando plazos y preparando el registro…"):
        try:
            resp, acts = chat_with_concierge(st.session_state.concierge_msgs)
        except Exception as e:
            resp, acts = f"Error en el Concierge ({str(e)[:250]}).", []
    st.session_state.concierge_msgs.append({"role": "assistant", "content": resp, "actions": acts})
    st.rerun()

def process_chat_message(user_text: str) -> None:
    st.session_state.chat_msgs.append({"role": "user", "content": user_text})
    with st.spinner("Consultando el acervo literario y preparando el análisis académico…"):
        try:
            resp = chat_reply(st.session_state.chat_msgs)
        except Exception as e:
            resp = f"Error al conectar con el modelo ({str(e)[:200]})."
    st.session_state.chat_msgs.append({"role": "assistant", "content": resp})
    st.rerun()

def process_assistant_message(user_text: str) -> None:
    st.session_state.asist_msgs.append({"role": "user", "content": user_text})
    with st.spinner("El Gestor Readout está orquestando las herramientas de préstamo…"):
        try:
            resp, new_thread, acts = chat_with_assistant(user_text, st.session_state.thread_id, st.session_state.asist_msgs)
            st.session_state.thread_id = new_thread
        except Exception as e:
            resp, acts = f"Error en la ejecución del Gestor ({str(e)[:250]}).", []
    st.session_state.asist_msgs.append({"role": "assistant", "content": resp, "actions": acts})
    st.rerun()

def is_pending_draft(msgs: list[dict]) -> bool:
    last = next((m.get("content", "") for m in reversed(msgs) if m.get("role") == "assistant"), "")
    return "Borrador de Solicitud" in last or "Borrador de tu Solicitud" in last or "Confirmación Requerida" in last

# ==============================================================================
# TAB 0: RECEPCIÓN · PRÉSTAMOS READOUT
# ==============================================================================
with tab_omni:
    section_head(
        "01", "Recepción",
        "Préstamos<br>en tres pasos",
        "Pida un libro por texto o por voz. La recepcionista confirma disponibilidad, toma sus datos, presenta un borrador y solo registra el préstamo cuando usted lo confirma."
    )

    col_flow, col_conv = st.columns([0.85, 1.6], gap="large")

    with col_flow:
        render_html("""
        <div class="rd-agenda">
          <div class="rd-agenda-row">
            <div class="rd-agenda-when"><b>Paso 1</b>Solicitud</div>
            <div class="rd-agenda-what"><strong>Pida el libro</strong><p>Se verifica el catálogo, la fianza y el plazo de devolución.</p></div>
          </div>
          <div class="rd-agenda-row">
            <div class="rd-agenda-when"><b>Paso 2</b>Borrador</div>
            <div class="rd-agenda-what"><strong>Revise los datos</strong><p>Correo y WhatsApp del lector, libros, montos y plazos.</p></div>
          </div>
          <div class="rd-agenda-row">
            <div class="rd-agenda-when"><b>Paso 3</b>Registro</div>
            <div class="rd-agenda-what"><strong>Confirme</strong><p>Se anota en Google Sheets y se envían la boleta y el recordatorio.</p></div>
          </div>
        </div>
        """)

        render_html('<p class="rd-label">Pruebe con</p>')
        with st.container(key="sug-omni"):
            if st.button("Préstamo con correo y WhatsApp", key="omni_sug1", width="stretch"):
                process_concierge_message("Hola, deseo solicitar 1 ejemplar de Clean Code y 1 ejemplar de Inteligencia Artificial. Mi correo es usuario@gmail.com y mi WhatsApp es 987509272.")
            if st.button("Reservar sala de lectura", key="omni_sug2", width="stretch"):
                process_concierge_message("Quisiera reservar una sala de lectura grupal para 4 investigadores este viernes. Mi correo es investigacion@instituto.org.")
            if st.button("Catálogo y plazos", key="omni_sug3", width="stretch"):
                process_concierge_message("¿Qué libros tienen disponibles en el catálogo de Readout y cuáles son sus condiciones de préstamo?")

        st.write("")
        with st.expander("Dictar la solicitud por voz", expanded=False):
            omni_mic = st.audio_input("Hable para dictar su solicitud de préstamo o reserva:", key="omni_voice_recorder")
            if omni_mic:
                if st.button("Enviar audio a la recepción", type="primary", width="stretch", key="btn_send_voice_omni"):
                    with st.spinner("Transcribiendo su voz con Whisper y procesando con la Recepción…"):
                        try:
                            audio_data = omni_mic.getvalue()
                            transcribed_text, _ = transcribe_audio(audio_data, "solicitud_voz_concierge.wav")
                        except Exception as e:
                            transcribed_text = f"Solicitud dictada por voz: {str(e)[:150]}"
                    if transcribed_text:
                        process_concierge_message(transcribed_text)

    with col_conv:
        with st.container(height=520, border=True, key="chat-omni"):
            if not st.session_state.concierge_msgs:
                render_html("""
                <div class="rd-empty">
                  <p class="rd-display rd-empty-big">Buenas<br>tardes.</p>
                  <p>¿Qué libro desea llevarse hoy? Escriba el título, o elija una de las solicitudes de ejemplo.</p>
                </div>
                """)
            else:
                for m in st.session_state.concierge_msgs:
                    with st.chat_message(m["role"]):
                        st.markdown(m["content"])
                        if m.get("actions"):
                            render_actions(m["actions"])

        # Si hay un borrador pendiente de confirmación, mostrar botones de acción directa
        if st.session_state.concierge_msgs and is_pending_draft(st.session_state.concierge_msgs):
            col_c1, col_c2 = st.columns([1.5, 1])
            with col_c1:
                if st.button("Confirmar y registrar el préstamo", type="primary", width="stretch", key="btn_confirm_order"):
                    process_concierge_message("Sí, confirmar")
            with col_c2:
                if st.button("Modificar solicitud", width="stretch", key="btn_modify_order"):
                    process_concierge_message("Deseo modificar mi solicitud de libros")

        omni_input = st.chat_input("Escriba su solicitud (ej. «Deseo prestar Clean Code»)…", key="concierge_chat_input")
        if omni_input:
            process_concierge_message(omni_input)

# ==============================================================================
# TAB 1: BIBLIÓFILOBOT (CHAT LITERARIO & ACADÉMICO)
# ==============================================================================
with tab_chat:
    section_head(
        "02", "Asesor literario",
        "Conversar<br>sobre libros",
        "Síntesis, contexto del autor y claves de lectura de literatura clásica y contemporánea, ingeniería de software, ciencia y filosofía."
    )

    with st.container(key="sug-asesor"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Principios de Clean Code", key="sug_clean", width="stretch"):
                process_chat_message("¿Cuáles son los principios fundamentales de Clean Code de Robert C. Martin?")
        with c2:
            if st.button("Macondo en Cien años de soledad", key="sug_cien", width="stretch"):
                process_chat_message("¿De qué trata Cien Años de Soledad y qué representa Macondo en la obra de García Márquez?")
        with c3:
            if st.button("Lecciones de El arte de la guerra", key="sug_arte", width="stretch"):
                process_chat_message("¿Cuáles son las lecciones estratégicas más importantes de El Arte de la Guerra de Sun Tzu?")
        with c4:
            if st.button("Breve historia del tiempo, explicada", key="sug_tiempo", width="stretch"):
                process_chat_message("Explícame los conceptos clave de Breve Historia del Tiempo de Stephen Hawking.")

    st.write("")

    # Mensajes de Chat con Contenedor Scrollable
    with st.container(height=520, border=True, key="chat-asesor"):
        if not st.session_state.chat_msgs:
            render_html("""
            <div class="rd-empty">
              <p class="rd-display rd-empty-big">¿Qué está<br>leyendo?</p>
              <p>Pregunte por una obra, un autor o una forma de leer mejor. Las respuestas incluyen síntesis, contexto y puntos clave.</p>
            </div>
            """)
        else:
            for m in st.session_state.chat_msgs:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

    # Chat Input
    prompt = st.chat_input("Escriba su consulta sobre libros, autores, reseñas o metodologías de lectura…")
    if prompt:
        process_chat_message(prompt)


# ==============================================================================
# TAB 2: TRANSCRIPTOR WHISPER (AUDIO A TEXTO)
# ==============================================================================
with tab_audio:
    section_head(
        "03", "Transcriptor",
        "De la voz<br>al registro",
        f"Notas de voz, pedidos de préstamo y reseñas dictadas se convierten en texto con <code>{esc(WHISPER_MODEL)}</code>, listo para enviarse al Gestor."
    )

    ultimo = st.session_state.transcripciones[0]["hora"] if st.session_state.transcripciones else "--:--:--"
    hh, mm, ss = (ultimo.split(":") + ["--", "--", "--"])[:3]
    n_tr = len(st.session_state.transcripciones)
    render_html(f"""
    <div class="rd-clock">
      <div>
        <span class="rd-eyebrow">Última transcripción · {n_tr} en esta sesión</span>
        <div class="rd-clock-digits">
          <div><strong>{hh}</strong><span>HORA</span></div>
          <div><strong class="rd-clock-sep">:</strong><span>&nbsp;</span></div>
          <div><strong>{mm}</strong><span>MIN</span></div>
          <div><strong class="rd-clock-sep">:</strong><span>&nbsp;</span></div>
          <div><strong>{ss}</strong><span>SEG</span></div>
        </div>
      </div>
      <div class="rd-clock-art">{sunburst_svg()}</div>
    </div>
    """)

    col_audio_left, col_audio_right = st.columns([1, 1.15], gap="large")

    with col_audio_left:
        render_html('<p class="rd-label">Entrada de audio</p>')

        if "audio_input_mode" not in st.session_state:
            st.session_state.audio_input_mode = "mic"

        with st.container(key="audio-mode"):
            col_b1, col_b2 = st.columns(2, gap="small")
            with col_b1:
                is_mic = st.session_state.audio_input_mode == "mic"
                if st.button("Micrófono", key="btn_select_mic", type="primary" if is_mic else "secondary", width="stretch"):
                    st.session_state.audio_input_mode = "mic"
                    st.rerun()
            with col_b2:
                is_file = st.session_state.audio_input_mode == "file"
                if st.button("Archivo", key="btn_select_file", type="primary" if is_file else "secondary", width="stretch"):
                    st.session_state.audio_input_mode = "file"
                    st.rerun()

        if st.session_state.audio_input_mode == "mic":
            mic_audio = st.audio_input("Presione el micrófono, dicte y detenga la grabación:", key="live_mic_recorder")

            if mic_audio:
                st.audio(mic_audio)
                if st.button("Transcribir grabación", type="primary", width="stretch", key="btn_tr_mic"):
                    data = mic_audio.getvalue()
                    with st.spinner("Transcribiendo su voz en vivo con Whisper…"):
                        try:
                            texto, es_demo = transcribe_audio(data, "grabacion_microfono.wav")
                        except Exception as e:
                            texto, es_demo = f"Error en transcripción: {str(e)[:250]}", DEMO

                    st.session_state.transcripciones.insert(0, {
                        "id": str(uuid.uuid4())[:8],
                        "archivo": f"Dictado por voz ({datetime.now().strftime('%H:%M:%S')})",
                        "texto": texto,
                        "demo": es_demo,
                        "hora": datetime.now().strftime("%H:%M:%S")
                    })
                    st.success("Voz transcrita exitosamente.")
                    st.rerun()

        elif st.session_state.audio_input_mode == "file":
            up_file = st.file_uploader(
                "Archivo de audio (MP3, WAV, M4A, OGG, MP4, WEBM)",
                type=["mp3", "wav", "m4a", "ogg", "mp4", "webm"],
            )

            if up_file:
                st.audio(up_file)
                if st.button("Transcribir archivo", type="primary", width="stretch", key="btn_tr_file"):
                    data = up_file.getvalue()
                    with st.spinner("Transcribiendo archivo con Whisper…"):
                        try:
                            texto, es_demo = transcribe_audio(data, up_file.name)
                        except Exception as e:
                            texto, es_demo = f"Error en transcripción: {str(e)[:250]}", DEMO

                    st.session_state.transcripciones.insert(0, {
                        "id": str(uuid.uuid4())[:8],
                        "archivo": up_file.name,
                        "texto": texto,
                        "demo": es_demo,
                        "hora": datetime.now().strftime("%H:%M:%S")
                    })
                    st.success("Transcripción completada con éxito.")
                    st.rerun()

    with col_audio_right:
        header_col1, header_col2 = st.columns([2, 1])
        with header_col1:
            render_html('<p class="rd-label">Resultados</p>')
        with header_col2:
            if st.session_state.transcripciones:
                if st.button("Limpiar historial", key="btn_clear_audios", width="stretch"):
                    st.session_state.transcripciones = []
                    st.rerun()

        if not st.session_state.transcripciones:
            render_html("""
            <div class="rd-agenda">
              <div class="rd-agenda-row">
                <div class="rd-agenda-when"><b>--:--</b>Sin audio</div>
                <div class="rd-agenda-what"><strong>Aún no hay transcripciones</strong><p>Grabe su voz o suba un archivo; el texto aparecerá aquí para revisarlo, descargarlo o enviarlo al Gestor.</p></div>
              </div>
            </div>
            """)
        else:
            for idx, item in enumerate(st.session_state.transcripciones):
                item_id = item.get("id", f"{idx}_{item.get('hora', '')}")
                tag = '<span class="rd-tag">Demo</span>' if item["demo"] else f'<span class="rd-tag rd-tag--live">{esc(WHISPER_MODEL)}</span>'
                render_html(f"""
                <div class="rd-log-head">
                  <span class="rd-mono">{esc(item['hora'])}</span>
                  <span>{esc(item['archivo'])}</span>
                  {tag}
                </div>
                """)

                st.text_area("Texto transcrito", value=item["texto"], height=95, key=f"tx_area_{item_id}", label_visibility="collapsed")

                c_act1, c_act2 = st.columns([1.5, 1])
                with c_act1:
                    if st.button("Enviar al Gestor", key=f"btn_send_{item_id}", type="primary", width="stretch"):
                        process_assistant_message(f"Procesa esta solicitud de préstamo dictada por audio: {item['texto'][:350]}")
                with c_act2:
                    st.download_button(
                        "Descargar TXT",
                        data=item["texto"],
                        file_name=f"transcripcion_{item['archivo']}.txt",
                        mime="text/plain",
                        key=f"dl_{item_id}",
                        width="stretch"
                    )


# ==============================================================================
# TAB 3: GESTOR READOUT (FUNCTION CALLING)
# ==============================================================================
with tab_asist:
    section_head(
        "04", "Gestor",
        "Órdenes<br>directas",
        "Pida en lenguaje natural que se registre un préstamo, se emita una boleta o se envíe un recordatorio; el Gestor ejecuta las herramientas y le resume lo que realmente ocurrió."
    )

    col_chat_asist, col_tools = st.columns([1.25, 0.85], gap="large")

    with col_chat_asist:
        with st.container(horizontal=True, key="sug-gestor"):
            if st.button("Emitir boleta por email", key="cmd_email"):
                process_assistant_message("Envía un correo de confirmación de préstamo de Clean Code a lector@universidad.edu.pe con plazo de 7 días.")
            if st.button("Registrar préstamo en Sheets", key="cmd_sheet"):
                process_assistant_message("Registra un préstamo de 2 ejemplares de Inteligencia Artificial y 1 Quijote con una fianza total de 50 soles.")

        # Chat del asistente con scroll independiente
        with st.container(height=480, border=True, key="chat-gestor"):
            if not st.session_state.asist_msgs:
                render_html("""
                <div class="rd-terminal">
                  <b>readout</b> gestor listo<br>
                  herramientas: registrar_sheet · enviar_email · enviar_whatsapp<br>
                  ejemplo: «Registra 2 ejemplares de El Principito para ana@correo.com»<br>
                  &gt; <span class="rd-caret"></span>
                </div>
                """)
            else:
                for m in st.session_state.asist_msgs:
                    with st.chat_message(m["role"]):
                        st.markdown(m["content"])
                        if m.get("actions"):
                            render_actions(m["actions"])

        # Si hay un borrador pendiente de confirmación en el asistente
        if st.session_state.asist_msgs and is_pending_draft(st.session_state.asist_msgs):
            col_ac1, col_ac2 = st.columns([1.5, 1])
            with col_ac1:
                if st.button("Confirmar operación", type="primary", width="stretch", key="btn_confirm_asist"):
                    process_assistant_message("Sí, confirmar")
            with col_ac2:
                if st.button("Modificar datos", width="stretch", key="btn_modify_asist"):
                    process_assistant_message("Deseo modificar mi solicitud")

        asist_input = st.chat_input("Pida una acción: registrar préstamo, emitir boleta, notificar por WhatsApp…", key="asist_chat_box")
        if asist_input:
            process_assistant_message(asist_input)

    with col_tools:
        with st.container(key="tools-panel"):
            render_html("""
            <h3 class="rd-display rd-panel-title">Disparo<br>directo</h3>
            <p class="rd-panel-cap">Ejecute cada conector por separado, sin pasar por la IA, para comprobar que funciona.</p>
            """)

            tool_tab1, tool_tab2, tool_tab3 = st.tabs(["Email", "Sheets", "WhatsApp"])

            with tool_tab1:
                to_email = st.text_input("Destinatario", "usuario@gmail.com", key="dir_email_to")
                sub_email = st.text_input("Asunto", "Confirmación de Préstamo de Libros · Readout", key="dir_email_sub")
                body_email = st.text_area("Cuerpo del correo", "Hola, confirmamos su préstamo de 1x Clean Code por 7 días. Código de Ticket Readout: RO-2026-0925.", key="dir_email_body", height=85)
                if st.button("Ejecutar send_email()", type="primary", width="stretch", key="btn_dir_email"):
                    res = send_email(to_email, sub_email, body_email)
                    if res.get("ok"):
                        st.success(f"Ejecución exitosa: {res.get('detail')}")
                    else:
                        st.warning(f"Resultado: {res.get('detail')}")

            with tool_tab2:
                tipo_sheet = st.selectbox("Tipo de registro", ["prestamo", "reserva", "devolucion", "incidencia"], key="dir_sheet_tipo")
                det_sheet = st.text_input("Detalle de libros", "1x Clean Code + 1x Cien Años de Soledad", key="dir_sheet_det")
                mon_sheet = st.text_input("Fianza / arancel (S/)", "25.00", key="dir_sheet_mon")
                if st.button("Ejecutar log_to_sheet()", type="primary", width="stretch", key="btn_dir_sheet"):
                    res = log_to_sheet(tipo_sheet, det_sheet, mon_sheet, "")
                    if res.get("ok"):
                        st.success(f"Ejecución exitosa: {res.get('detail')}")
                    else:
                        st.warning(f"Resultado: {res.get('detail')}")

            with tool_tab3:
                w_to = st.text_input("Teléfono / WhatsApp (ej. 987509272 o 51987509272@c.us)", "987509272", key="dir_wsp_to")
                w_msg = st.text_area("Mensaje", "Hola, su préstamo en Readout ha sido registrado. Recuerde devolver los ejemplares antes de la fecha límite.", key="dir_wsp_msg", height=85)
                if st.button("Ejecutar send_whatsapp()", type="primary", width="stretch", key="btn_dir_wsp"):
                    res = send_whatsapp(w_to, w_msg)
                    if res.get("ok"):
                        st.success(f"Ejecución exitosa: {res.get('detail')}")
                    else:
                        st.warning(f"Resultado: {res.get('detail')}")


# ==============================================================================
# TAB 4: AUDITORÍA & LOGS DE OPERACIÓN
# ==============================================================================
def fmt_at(value) -> str:
    """Normaliza marcas de tiempo ISO a 'AAAA-MM-DD · HH:MM:SS'."""
    s = str(value or "")[:19]
    return esc(s.replace("T", " · ")) if s else "—"

with tab_logs:
    section_head(
        "05", "Auditoría",
        "Todo lo que<br>se ejecutó",
        "Historial persistente de correos, registros y mensajes disparados por la Recepción, el Gestor y el disparo directo de herramientas."
    )

    render_html(f"""
    <div class="rd-counters">
      <div><strong>{metrics['email_total']}</strong><span>Correos</span></div>
      <div><strong>{metrics['auto_total']}</strong><span>Registros</span></div>
      <div><strong>{metrics['wsp_total']}</strong><span>WhatsApp</span></div>
    </div>
    """)

    log_sub1, log_sub2, log_sub3 = st.tabs(["Correos", "Hoja de registros", "WhatsApp"])
    data_dir = Path("data")

    with log_sub1:
        email_file = data_dir / "email_log.jsonl"
        lines = [l for l in email_file.read_text(encoding="utf-8").splitlines() if l.strip()] if email_file.exists() else []
        if lines:
            rows = []
            for line in reversed(lines[-15:]):
                try:
                    record = json.loads(line)
                except Exception:
                    rows.append(f'<div class="rd-timeline-row"><div class="rd-timeline-when">—</div><div><pre>{esc_block(line)}</pre></div></div>')
                    continue
                tag = '<span class="rd-tag rd-tag--live">SMTP real</span>' if record.get("mode") == "smtp" else '<span class="rd-tag">Simulado</span>'
                rows.append(f"""
                <div class="rd-timeline-row">
                  <div class="rd-timeline-when">{fmt_at(record.get('at'))}<br>{tag}</div>
                  <div>
                    <p class="rd-timeline-title">{esc(str(record.get('to', '')))}</p>
                    <p class="rd-timeline-sub">{esc(str(record.get('subject', '')))}</p>
                    <details><summary>Ver mensaje</summary><pre>{esc_block(str(record.get('body', '')))}</pre></details>
                  </div>
                </div>""")
            render_html(f'<div class="rd-timeline">{"".join(rows)}</div>')
            if len(lines) > 15:
                st.caption(f"Mostrando los 15 envíos más recientes de {len(lines)}.")
        else:
            st.info("Aún no se han registrado correos. Realice una prueba en la pestaña Gestor.")

    with log_sub2:
        sheet_file = data_dir / "sheets_log.csv"
        content = sheet_file.read_text(encoding="utf-8").strip() if sheet_file.exists() else ""
        rows = list(csv.DictReader(content.splitlines())) if content else []
        if rows:
            st.dataframe(rows[::-1], width="stretch")
            st.download_button(
                "Descargar registro CSV",
                data=content,
                file_name="sheets_log.csv",
                mime="text/csv",
            )
        else:
            st.info("La hoja de registros está vacía por el momento.")

    with log_sub3:
        wsp_file = data_dir / "whatsapp_log.jsonl"
        lines = [l for l in wsp_file.read_text(encoding="utf-8").splitlines() if l.strip()] if wsp_file.exists() else []
        if lines:
            rows = []
            for line in reversed(lines[-15:]):
                try:
                    record = json.loads(line)
                except Exception:
                    rows.append(f'<div class="rd-timeline-row"><div class="rd-timeline-when">—</div><div><pre>{esc_block(line)}</pre></div></div>')
                    continue
                tag = '<span class="rd-tag rd-tag--live">WAHA real</span>' if record.get("mode") == "waha" else '<span class="rd-tag">Simulado</span>'
                rows.append(f"""
                <div class="rd-timeline-row">
                  <div class="rd-timeline-when">{fmt_at(record.get('at'))}<br>{tag}</div>
                  <div>
                    <p class="rd-timeline-title">{esc(str(record.get('to', '')))}</p>
                    <p class="rd-quote">{esc_block(str(record.get('message', '')))}</p>
                  </div>
                </div>""")
            render_html(f'<div class="rd-timeline">{"".join(rows)}</div>')
            if len(lines) > 15:
                st.caption(f"Mostrando los 15 mensajes más recientes de {len(lines)}.")
        else:
            st.info("Aún no hay mensajes de WhatsApp registrados.")
