import csv
import io
import json
import os
import re
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
    page_title="Readout IA · Suite de Gestión Bibliotecaria & Préstamo de Libros",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper para renderizar HTML sin que markdown-it active bloques de código
def render_html(html_str: str) -> None:
    cleaned = re.sub(r'^[ \t]+', '', html_str.strip(), flags=re.MULTILINE)
    st.markdown(cleaned, unsafe_allow_html=True)

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

# ---------- CARGA DE TAILWIND CSS COMPILADO + ESTILOS GLOBALES ----------
TAILWIND_CSS_PATH = Path(__file__).resolve().parent / "static" / "tailwind.css"
tailwind_css = ""
if TAILWIND_CSS_PATH.exists():
    tailwind_css = TAILWIND_CSS_PATH.read_text(encoding="utf-8")

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700;9..144,800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

if tailwind_css:
    st.markdown(f"<style>\n{tailwind_css}\n</style>", unsafe_allow_html=True)

st.markdown("""
<style>
/* Corrección de superposición de texto de ligadura en cargador de archivos */
[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneIcon"],
[data-testid="stFileUploaderDropzone"] [data-testid*="stIconMaterial"],
[data-testid="stFileUploaderDropzone"] button > span:first-child:not(:only-child) {
  display: none !important;
}
[data-testid="stFileUploaderDropzone"] button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 0.5rem !important;
  padding: 0.55rem 1.15rem !important;
  font-size: 0.88rem !important;
  font-weight: 700 !important;
}

/* Contenedor de chat con scroll independiente y estilo ejecutivo glass */
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 16px !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  background: rgba(15, 23, 42, 0.5) !important;
  backdrop-filter: blur(10px) !important;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3) !important;
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
  scrollbar-width: thin !important;
  scrollbar-color: rgba(99, 102, 241, 0.45) rgba(15, 23, 42, 0.6) !important;
  padding: 0.75rem 0.5rem !important;
}

[data-testid="stVerticalBlockBorderWrapper"] > div::-webkit-scrollbar {
  width: 6px !important;
}

[data-testid="stVerticalBlockBorderWrapper"] > div::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.6) !important;
  border-radius: 9999px !important;
}

[data-testid="stVerticalBlockBorderWrapper"] > div::-webkit-scrollbar-thumb {
  background: rgba(99, 102, 241, 0.45) !important;
  border-radius: 9999px !important;
}

[data-testid="stVerticalBlockBorderWrapper"] > div::-webkit-scrollbar-thumb:hover {
  background: rgba(99, 102, 241, 0.8) !important;
}
</style>
""", unsafe_allow_html=True)


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
            if r.status_code == 200:
                waha_ok = True
                waha_detail = f"Servidor Docker WAHA Activo ({waha_url})"
            else:
                waha_detail = f"WAHA respondió HTTP {r.status_code}"
        except Exception:
            waha_detail = f"Servidor WAHA inaccesible en {waha_url}"
            
    tools_count = sum([1 for ok in [smtp_ok, sheets_ok, waha_ok] if ok])
    tools_all_connected = bool(smtp_ok and sheets_ok and waha_ok)
    
    if tools_all_connected and ai_connected:
        system_status = "3/3 Conectadas"
        system_label = "Conectado (3/3)"
        system_connected = True
        sys_color = "#34D399"
        sys_dot_color = "#10B981"
        sys_bg_gradient = "rgba(16,185,129,0.25) 0%, rgba(5,150,105,0.1) 100%"
        sys_border = "rgba(16,185,129,0.45)"
        sys_shadow = "rgba(16,185,129,0.25)"
        sys_badge_bg = "rgba(16,185,129,0.18)"
    elif tools_count > 0:
        system_status = f"{tools_count}/3 Conectadas"
        system_label = f"Conectado ({tools_count}/3)"
        system_connected = False
        sys_color = "#FBBF24"
        sys_dot_color = "#F59E0B"
        sys_bg_gradient = "rgba(245,158,11,0.25) 0%, rgba(217,119,6,0.1) 100%"
        sys_border = "rgba(245,158,11,0.45)"
        sys_shadow = "rgba(245,158,11,0.25)"
        sys_badge_bg = "rgba(245,158,11,0.18)"
    else:
        system_status = "0/3 Simulación"
        system_label = "Simulación (0/3)"
        system_connected = False
        sys_color = "#60A5FA"
        sys_dot_color = "#3B82F6"
        sys_bg_gradient = "rgba(59,130,246,0.25) 0%, rgba(37,99,235,0.1) 100%"
        sys_border = "rgba(59,130,246,0.45)"
        sys_shadow = "rgba(59,130,246,0.25)"
        sys_badge_bg = "rgba(59,130,246,0.18)"
    
    return {
        "ai_connected": ai_connected,
        "provider_name": provider_name,
        "chat_model": CHAT_MODEL,
        "whisper_model": WHISPER_MODEL,
        "assistant_model": ASSISTANT_MODEL,
        "demo": demo_mode,
        "smtp": {
            "connected": smtp_ok,
            "host": smtp_host,
            "user": smtp_user,
            "port": smtp_port,
            "detail": f"{smtp_host}:{smtp_port} ({smtp_user})" if smtp_ok else "No configurado (Simulado en data/email_log.jsonl)"
        },
        "sheets": {
            "connected": sheets_ok,
            "sheet_id": sheet_id,
            "sa_file": sa_json,
            "detail": f"Service Account activa ({sheet_id[:16]}...)" if sheets_ok else "No configurado (CSV local data/sheets_log.csv)"
        },
        "waha": {
            "connected": waha_ok,
            "url": waha_url,
            "detail": waha_detail
        },
        "tools_count": tools_count,
        "tools_all_connected": tools_all_connected,
        "system_connected": system_connected,
        "system_label": system_label,
        "system_status": system_status,
        "sys_color": sys_color,
        "sys_dot_color": sys_dot_color,
        "sys_bg_gradient": sys_bg_gradient,
        "sys_border": sys_border,
        "sys_shadow": sys_shadow,
        "sys_badge_bg": sys_badge_bg
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

# ---------- HERO BANNER CON ESTILOS EJECUTIVOS ----------
badge_html = (
    f'<span style="display:inline-flex; align-items:center; gap:6px; padding:4px 12px; border-radius:9999px; font-size:0.75rem; font-weight:800; background:rgba(16,185,129,0.18); color:#34D399; border:1px solid rgba(16,185,129,0.4); box-shadow:0 2px 8px rgba(16,185,129,0.15);">'
    f'<span style="width:7px; height:7px; border-radius:50%; background:#10B981; display:inline-block; box-shadow:0 0 8px #10B981;"></span> MODO · {health["provider_name"].upper()} CONECTADO</span>'
    if health["ai_connected"] else
    '<span style="display:inline-flex; align-items:center; gap:6px; padding:4px 12px; border-radius:9999px; font-size:0.75rem; font-weight:800; background:rgba(245,158,11,0.18); color:#FBBF24; border:1px solid rgba(245,158,11,0.4); box-shadow:0 2px 8px rgba(245,158,11,0.15);">'
    '<span style="width:7px; height:7px; border-radius:50%; background:#F59E0B; display:inline-block; box-shadow:0 0 8px #F59E0B;"></span> MODO · SIMULACIÓN ACTIVA</span>'
)

render_html(f"""
<div class="sa-hero-card">
  <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:flex-start; gap:1.5rem; position:relative; z-index:10;">
    <div style="flex:1 1 500px; max-width:760px;">
      <h1 class="sa-hero-title">
        Readout <span class="sa-hero-gradient-text">Inteligencia Artificial</span>
      </h1>
      <p class="sa-hero-desc">
        Suite integral de gestión bibliotecaria y préstamo de libros: asesor literario & académico, transcriptor de solicitudes de lectura por voz con 
        <strong style="color:#FFFFFF;">Whisper</strong> y automatización de préstamos Readout (Email, Google Sheets, WhatsApp) vía <strong style="color:#FFFFFF;">OpenAI Assistants API</strong>.
      </p>
    </div>
    <div style="display:flex; flex-direction:column; align-items:flex-start; md:align-items:flex-end; gap:0.75rem; flex-shrink:0;">
      <div>{badge_html}</div>
      <div style="display:flex; flex-wrap:wrap; gap:0.5rem;">
        <span class="sa-model-pill" title="Modelo de Chat Completions activo">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M6 6h10"/><path d="M6 10h10"/></svg>
          {health['chat_model']}
        </span>
        <span class="sa-model-pill" title="Modelo de Whisper Audio activo">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
          {health['whisper_model']}
        </span>
        <span class="sa-model-pill" title="Modelo de Assistants API activo">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          {health['assistant_model']}
        </span>
      </div>
    </div>
  </div>
</div>
""")

# ---------- TARJETAS KPI DASHBOARD CON ICONOS BRILLANTES ----------
render_html(f"""
<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:1rem; margin-bottom:1.5rem;">
  <div class="sa-kpi-card">
    <div class="sa-kpi-icon" style="width:48px; height:48px; min-width:48px; border-radius:14px; background:linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(79,70,229,0.1) 100%); border:1.5px solid rgba(99,102,241,0.45); display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px rgba(99,102,241,0.25); flex-shrink:0;">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"></path>
        <path d="M6 6h10"></path>
        <path d="M6 10h10"></path>
      </svg>
    </div>
    <div style="min-width:0;">
      <p class="sa-kpi-label">Chat Literario & Académico</p>
      <p class="sa-kpi-value">{metrics['chat_total']}</p>
    </div>
  </div>

  <div class="sa-kpi-card">
    <div class="sa-kpi-icon" style="width:48px; height:48px; min-width:48px; border-radius:14px; background:linear-gradient(135deg, rgba(245,158,11,0.25) 0%, rgba(217,119,6,0.1) 100%); border:1.5px solid rgba(245,158,11,0.45); display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px rgba(245,158,11,0.25); flex-shrink:0;">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="23"></line>
        <line x1="8" y1="23" x2="16" y2="23"></line>
      </svg>
    </div>
    <div style="min-width:0;">
      <p class="sa-kpi-label">Audios Transcritos</p>
      <p class="sa-kpi-value">{metrics['audio_total']}</p>
    </div>
  </div>

  <div class="sa-kpi-card">
    <div class="sa-kpi-icon" style="width:48px; height:48px; min-width:48px; border-radius:14px; background:linear-gradient(135deg, rgba(16,185,129,0.25) 0%, rgba(5,150,105,0.1) 100%); border:1.5px solid rgba(16,185,129,0.45); display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px rgba(16,185,129,0.25); flex-shrink:0;">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
      </svg>
    </div>
    <div style="min-width:0;">
      <p class="sa-kpi-label">Préstamos Readout</p>
      <p class="sa-kpi-value">{metrics['auto_total']}</p>
    </div>
  </div>

  <div class="sa-kpi-card">
    <div class="sa-kpi-icon" style="width:48px; height:48px; min-width:48px; border-radius:14px; background:linear-gradient(135deg, {health['sys_bg_gradient']}); border:1.5px solid {health['sys_border']}; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px {health['sys_shadow']}; flex-shrink:0;">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{health['sys_color']}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
      </svg>
    </div>
    <div style="flex:1; min-width:0;">
      <p class="sa-kpi-label">Estado del Sistema</p>
      <div style="display:flex; align-items:center; gap:6px; margin:2px 0;">
        <span style="width:8px; height:8px; border-radius:50%; background:{health['sys_dot_color']}; box-shadow:0 0 8px {health['sys_dot_color']}; display:inline-block; flex-shrink:0;"></span>
        <p style="font-size:1.35rem; font-weight:800; color:{health['sys_color']}; margin:0; line-height:1.15;">{health['system_status']}</p>
      </div>
      <div style="display:flex; align-items:center; gap:6px; font-size:0.68rem; font-weight:700; color:#94A3B8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
        <span style="display:inline-flex; align-items:center; gap:3px;"><span style="width:5px; height:5px; border-radius:50%; background:{'#10B981' if health['smtp']['connected'] else '#F59E0B'}; display:inline-block;"></span> Email</span>
        <span style="color:#475569;">·</span>
        <span style="display:inline-flex; align-items:center; gap:3px;"><span style="width:5px; height:5px; border-radius:50%; background:{'#10B981' if health['sheets']['connected'] else '#F59E0B'}; display:inline-block;"></span> Sheets</span>
        <span style="color:#475569;">·</span>
        <span style="display:inline-flex; align-items:center; gap:3px;"><span style="width:5px; height:5px; border-radius:50%; background:{'#10B981' if health['waha']['connected'] else '#F59E0B'}; display:inline-block;"></span> WAHA</span>
      </div>
    </div>
  </div>
</div>
""")

# ---------- BARRA LATERAL (SIDEBAR) ----------
with st.sidebar:
    render_html("""
    <div class="sa-sidebar-brand">
      <div class="sa-sidebar-avatar" style="background:linear-gradient(135deg, #6366F1 0%, #4F46E5 100%); color:#FFFFFF;">RO</div>
      <div>
        <h3 class="sa-sidebar-title">Readout</h3>
        <p class="sa-sidebar-sub">Gestión Bibliotecaria Readout</p>
      </div>
    </div>
    """)

    st.markdown("#### Diagnóstico de IA & Modelos")
    
    if health["ai_connected"]:
        render_html(f"""
        <div class="sa-diag-box sa-diag-real">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-weight:800; font-size:0.88rem;">[CONECTADO] {health['provider_name']}</span>
            <span style="width:8px; height:8px; border-radius:50%; background:#10B981; display:inline-block; box-shadow:0 0 6px #10B981;"></span>
          </div>
          <div style="font-size:0.78rem; line-height:1.45; color:#E2E8F0;">
            • Chat: <code>{health['chat_model']}</code><br>
            • Whisper: <code>{health['whisper_model']}</code><br>
            • Asistente: <code>{health['assistant_model']}</code>
          </div>
        </div>
        """)
    else:
        render_html(f"""
        <div class="sa-diag-box sa-diag-demo">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-weight:800; font-size:0.88rem;">[DESCONECTADO] Modo Demo</span>
            <span style="width:8px; height:8px; border-radius:50%; background:#F59E0B; display:inline-block; box-shadow:0 0 6px #F59E0B;"></span>
          </div>
          <div style="font-size:0.78rem; line-height:1.45;">
            <code>FORCE_MOCK_MODE=true</code> o API Key no configurada. Ejecutando simulación bibliográfica local.
          </div>
        </div>
        """)

    st.markdown("#### Estado de Integraciones (Tools)")
    
    badge_conn = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:0.75rem; font-weight:800; color:#34D399; background:rgba(16,185,129,0.15); padding:2px 8px; border-radius:6px; border:1px solid rgba(16,185,129,0.3);"><span style="width:6px; height:6px; border-radius:50%; background:#10B981; display:inline-block; box-shadow:0 0 6px #10B981;"></span> Conectado</span>'
    badge_disc = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:0.75rem; font-weight:800; color:#F87171; background:rgba(239,68,68,0.15); padding:2px 8px; border-radius:6px; border:1px solid rgba(239,68,68,0.3);"><span style="width:6px; height:6px; border-radius:50%; background:#EF4444; display:inline-block; box-shadow:0 0 6px #EF4444;"></span> Desconectado</span>'
    
    smtp_badge = badge_conn if health["smtp"]["connected"] else badge_disc
    sheets_badge = badge_conn if health["sheets"]["connected"] else badge_disc
    waha_badge = badge_conn if health["waha"]["connected"] else badge_disc
    
    render_html(f"""
    <div class="sa-card" style="padding:0.9rem 1rem; margin-bottom:0.75rem;">
      <div style="margin-bottom:0.65rem; border-bottom:1px solid #1F2937; padding-bottom:0.45rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:700; color:#FFFFFF; font-size:0.84rem; display:inline-flex; align-items:center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle; display:inline-block; margin-right:6px;"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
            Email SMTP
          </span>
          {smtp_badge}
        </div>
        <div style="font-size:0.72rem; color:#94A3B8; margin-top:2px; font-family:'JetBrains Mono',monospace;">{health['smtp']['detail']}</div>
      </div>
      <div style="margin-bottom:0.65rem; border-bottom:1px solid #1F2937; padding-bottom:0.45rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:700; color:#FFFFFF; font-size:0.84rem; display:inline-flex; align-items:center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle; display:inline-block; margin-right:6px;"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 13h8"/><path d="M8 17h8"/><path d="M10 9h2"/></svg>
            Google Sheets / Readout
          </span>
          {sheets_badge}
        </div>
        <div style="font-size:0.72rem; color:#94A3B8; margin-top:2px; font-family:'JetBrains Mono',monospace;">{health['sheets']['detail']}</div>
      </div>
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:700; color:#FFFFFF; font-size:0.84rem; display:inline-flex; align-items:center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle; display:inline-block; margin-right:6px;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            WhatsApp WAHA
          </span>
          {waha_badge}
        </div>
        <div style="font-size:0.72rem; color:#94A3B8; margin-top:2px; font-family:'JetBrains Mono',monospace;">{health['waha']['detail']}</div>
      </div>
    </div>
    """)

    if st.button("Verificar Conexión en Vivo", key="btn_test_tools", use_container_width=True):
        st.rerun()

    st.divider()

    st.markdown("#### Control de Sesión")
    if st.button("Reiniciar Sesión", use_container_width=True):
        st.session_state.concierge_msgs = []
        st.session_state.chat_msgs = []
        st.session_state.asist_msgs = []
        st.session_state.thread_id = None
        st.session_state.transcripciones = []
        st.success("Sesión reiniciada con éxito.")
        st.rerun()

    if st.button("Limpiar Datos y Logs (0)", use_container_width=True):
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
    "Recepción · Préstamos Readout",
    "BibliófiloBot · Asesor Literario",
    "Transcriptor · Whisper Audio",
    "Gestor Readout · Automatización",
    "Auditoría · Logs de Préstamos"
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

# ==============================================================================
# TAB 0: RECEPCIÓN · PRÉSTAMOS READOUT
# ==============================================================================
with tab_omni:
    render_html("""
    <div style="margin-bottom:1.25rem;">
      <h2 style="font-size:1.6rem; font-weight:800; margin:0; color:#FFFFFF; font-family:'Fraunces',serif;">Recepción Bibliotecaria · Flujo de Préstamo Omnicanal</h2>
      <p style="color:#94A3B8; font-size:0.9rem; margin:4px 0 0 0;">
        Experiencia de atención bibliotecaria: solicite libros por <strong>Voz (Whisper)</strong> o <strong>Texto</strong>. La recepcionista verificará el catálogo, solicitará sus datos personales (correo y WhatsApp), presentará el borrador formal con fianza y plazos, y tras su confirmación explícita, registrará el préstamo en <strong>Google Sheets / Readout</strong> y enviará las boletas por <strong>Email</strong> y <strong>WhatsApp</strong>.
      </p>
    </div>
    """)

    # Sugerencias rápidas de flujo completo
    st.markdown("<p style='font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#94A3B8; margin-bottom:0.6rem;'>SOLICITUDES DE EJEMPLO:</p>", unsafe_allow_html=True)
    c_omni1, c_omni2, c_omni3 = st.columns(3)
    with c_omni1:
        if st.button("Préstamo de Libros con Correo y WhatsApp", key="omni_sug1", use_container_width=True):
            process_concierge_message("Hola, deseo solicitar 1 ejemplar de Clean Code y 1 ejemplar de Inteligencia Artificial. Mi correo es usuario@gmail.com y mi WhatsApp es 987509272.")
    with c_omni2:
        if st.button("Reserva de Sala de Lectura", key="omni_sug2", use_container_width=True):
            process_concierge_message("Quisiera reservar una sala de lectura grupal para 4 investigadores este viernes. Mi correo es investigacion@instituto.org.")
    with c_omni3:
        if st.button("Consultar Catálogo y Plazos de Préstamo", key="omni_sug3", use_container_width=True):
            process_concierge_message("¿Qué libros tienen disponibles en el catálogo de Readout y cuáles son sus condiciones de préstamo?")

    st.write("")

    # Card de Entrada por Voz en Vivo integrada directamente en el Chat
    with st.expander("Dictado por Micrófono en Vivo (Voz a Texto con Whisper)", expanded=False):
        col_v1, col_v2 = st.columns([2, 1])
        with col_v1:
            omni_mic = st.audio_input("Hable para dictar su solicitud de préstamo o reserva:", key="omni_voice_recorder")
        with col_v2:
            st.markdown("<p style='font-size:0.8rem; color:#94A3B8; margin-top:1.8rem;'>Grabe su voz y presione enviar para procesarla con Whisper:</p>", unsafe_allow_html=True)
            if omni_mic:
                if st.button("Enviar Audio a la Recepción", type="primary", use_container_width=True, key="btn_send_voice_omni"):
                    with st.spinner("Transcribiendo su voz con Whisper y procesando con la Recepción…"):
                        try:
                            audio_data = omni_mic.getvalue()
                            transcribed_text, _ = transcribe_audio(audio_data, "solicitud_voz_concierge.wav")
                        except Exception as e:
                            transcribed_text = f"Solicitud dictada por voz: {str(e)[:150]}"
                    if transcribed_text:
                        process_concierge_message(transcribed_text)

    # Contenedor de Chat Omnicanal con Scroll Independiente
    with st.container(height=520, border=True):
        if not st.session_state.concierge_msgs:
            render_html("""
            <div class="sa-empty-state" style="margin-top:1.5rem;">
              <div style="width:52px; height:52px; margin:0 auto 12px auto; border-radius:14px; background:linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(79,70,229,0.1) 100%); border:1.5px solid rgba(99,102,241,0.45); color:#C7D2FE; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px rgba(99,102,241,0.25);">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"></path>
                  <path d="M6 6h10"></path>
                  <path d="M6 10h10"></path>
                </svg>
              </div>
              <h3 style="font-weight:800; color:#FFFFFF; font-size:1.15rem; margin:0 0 6px 0;">Recepción Bibliotecaria Lista</h3>
              <p style="color:#94A3B8; font-size:0.9rem; max-width:480px; margin:0 auto; line-height:1.5;">
                Dicte por voz o escriba el libro que desea solicitar. La recepcionista verificará la disponibilidad, solicitará sus datos de contacto y le pedirá confirmación antes de emitir el préstamo en Google Sheets / Readout.
              </p>
            </div>
            """)
        else:
            for m in st.session_state.concierge_msgs:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    if "actions" in m and m["actions"]:
                        for act in m["actions"]:
                            is_email = "Email" in act
                            is_sheet = "Google Sheets" in act or "Sheets" in act or "Readout" in act
                            color = "#60A5FA" if is_email else ("#34D399" if is_sheet else "#FBBF24")
                            bg = "rgba(59,130,246,0.18)" if is_email else ("rgba(16,185,129,0.18)" if is_sheet else "rgba(245,158,11,0.18)")
                            border = "rgba(59,130,246,0.4)" if is_email else ("rgba(16,185,129,0.4)" if is_sheet else "rgba(245,158,11,0.4)")
                            
                            render_html(f"""
                            <span style="display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:8px; font-size:0.75rem; font-weight:700; background:{bg}; color:{color}; border:1px solid {border}; margin:4px 4px 4px 0;">
                              <span style="width:6px; height:6px; border-radius:50%; background:{color}; display:inline-block;"></span>
                              {act}
                            </span>
                            """)

    # Si hay un borrador pendiente de confirmación, mostrar botones de acción directa
    if st.session_state.concierge_msgs:
        last_asst_msg = next((m.get("content", "") for m in reversed(st.session_state.concierge_msgs) if m.get("role") == "assistant"), "")
        if "Borrador de Solicitud" in last_asst_msg or "Borrador de tu Solicitud" in last_asst_msg or "Confirmación Requerida" in last_asst_msg:
            col_c1, col_c2 = st.columns([1.5, 1])
            with col_c1:
                if st.button("Confirmar y Registrar Préstamo en Google Sheets, Email y WhatsApp", type="primary", use_container_width=True, key="btn_confirm_order"):
                    process_concierge_message("Sí, confirmar")
            with col_c2:
                if st.button("Modificar Solicitud / Datos", use_container_width=True, key="btn_modify_order"):
                    process_concierge_message("Deseo modificar mi solicitud de libros")

    omni_input = st.chat_input("Escriba su solicitud de préstamo o consulta a la recepción (ej. 'Deseo prestar Clean Code')...", key="concierge_chat_input")
    if omni_input:
        process_concierge_message(omni_input)

# ==============================================================================
# TAB 1: BIBLIÓFILOBOT (CHAT LITERARIO & ACADÉMICO)
# ==============================================================================
with tab_chat:
    render_html("""
    <div style="margin-bottom:1.25rem;">
      <h2 style="font-size:1.6rem; font-weight:800; margin:0; color:#FFFFFF; font-family:'Fraunces',serif;">BibliófiloBot · Asesor Literario & Académico</h2>
      <p style="color:#94A3B8; font-size:0.9rem; margin:4px 0 0 0;">Conversaciones sobre literatura clásica y contemporánea, libros de ingeniería de software, física, ciencias de datos, filosofía y recomendaciones de lectura.</p>
    </div>
    """)

    st.markdown("<p style='font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#94A3B8; margin-bottom:0.6rem;'>CONSULTAS ACADÉMICAS SUGERIDAS:</p>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        if st.button("Clean Code (Uncle Bob)", key="sug_clean", use_container_width=True):
            process_chat_message("¿Cuáles son los principios fundamentales de Clean Code de Robert C. Martin?")
    with c2:
        if st.button("Cien Años de Soledad", key="sug_cien", use_container_width=True):
            process_chat_message("¿De qué trata Cien Años de Soledad y qué representa Macondo en la obra de García Márquez?")
    with c3:
        if st.button("El Arte de la Guerra", key="sug_arte", use_container_width=True):
            process_chat_message("¿Cuáles son las lecciones estratégicas más importantes de El Arte de la Guerra de Sun Tzu?")
    with c4:
        if st.button("Breve Historia del Tiempo", key="sug_tiempo", use_container_width=True):
            process_chat_message("Explícame los conceptos clave de Breve Historia del Tiempo de Stephen Hawking.")

    st.write("")

    # Mensajes de Chat con Contenedor Scrollable
    with st.container(height=520, border=True):
        if not st.session_state.chat_msgs:
            render_html("""
            <div class="sa-empty-state" style="margin-top:1.5rem;">
              <div style="width:52px; height:52px; margin:0 auto 12px auto; border-radius:14px; background:linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(79,70,229,0.1) 100%); border:1.5px solid rgba(99,102,241,0.45); color:#C7D2FE; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px rgba(99,102,241,0.25);">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"></path>
                  <path d="M6 6h10"></path>
                  <path d="M6 10h10"></path>
                </svg>
              </div>
              <h3 style="font-weight:800; color:#FFFFFF; font-size:1.15rem; margin:0 0 6px 0;">Inicie su consulta bibliográfica</h3>
              <p style="color:#94A3B8; font-size:0.9rem; max-width:440px; margin:0 auto; line-height:1.5;">Seleccione una de las sugerencias arriba o escriba directamente cualquier pregunta sobre obras, autores o metodologías de lectura.</p>
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
    render_html("""
    <div style="margin-bottom:1.25rem;">
      <h2 style="font-size:1.6rem; font-weight:800; margin:0; color:#FFFFFF; font-family:'Fraunces',serif;">Transcriptor de Audios de Biblioteca & Solicitudes de Lectura (Whisper)</h2>
      <p style="color:#94A3B8; font-size:0.9rem; margin:4px 0 0 0;">Convierte notas de voz, pedidos de préstamo y reseñas literarias dictadas en texto estructurado mediante el modelo <code>whisper-1</code> de OpenAI.</p>
    </div>
    """)

    col_audio_left, col_audio_right = st.columns([1, 1], gap="large")

    with col_audio_left:
        st.markdown("### Entrada de Audio")
        st.caption("Seleccione el método para ingresar el audio:")
        
        if "audio_input_mode" not in st.session_state:
            st.session_state.audio_input_mode = "mic"

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            is_mic = st.session_state.audio_input_mode == "mic"
            if st.button("Micrófono en Vivo", key="btn_select_mic", type="primary" if is_mic else "secondary", use_container_width=True):
                st.session_state.audio_input_mode = "mic"
                st.rerun()
        with col_b2:
            is_file = st.session_state.audio_input_mode == "file"
            if st.button("Subir Archivo de Audio", key="btn_select_file", type="primary" if is_file else "secondary", use_container_width=True):
                st.session_state.audio_input_mode = "file"
                st.rerun()

        st.write("")

        if st.session_state.audio_input_mode == "mic":
            st.markdown("<p style='font-size:0.85rem; color:#CBD5E1; margin:4px 0 8px 0;'>Presione el <strong>micrófono</strong>, dicte la solicitud de préstamo o reseña y presione detener para procesar:</p>", unsafe_allow_html=True)
            mic_audio = st.audio_input("Dictado por voz en vivo:", key="live_mic_recorder")
            
            if mic_audio:
                st.audio(mic_audio)
                if st.button("Transcribir Grabación de Voz", type="primary", use_container_width=True, key="btn_tr_mic"):
                    data = mic_audio.getvalue()
                    with st.spinner("Transcribiendo su voz en vivo con Whisper…"):
                        try:
                            texto, es_demo = transcribe_audio(data, "grabacion_microfono.wav")
                        except Exception as e:
                            texto, es_demo = f"Error en transcripción: {str(e)[:250]}", DEMO
                    
                    import uuid
                    st.session_state.transcripciones.insert(0, {
                        "id": str(uuid.uuid4())[:8],
                        "archivo": f"Dictado por Voz ({datetime.now().strftime('%H:%M:%S')})",
                        "texto": texto,
                        "demo": es_demo,
                        "hora": datetime.now().strftime("%H:%M:%S")
                    })
                    st.success("Voz transcrita exitosamente.")
                    st.rerun()

        elif st.session_state.audio_input_mode == "file":
            st.markdown("<p style='font-size:0.85rem; color:#CBD5E1; margin:4px 0 8px 0;'>Seleccione o arrastre un archivo de audio (MP3, WAV, M4A, OGG, MP4, WEBM):</p>", unsafe_allow_html=True)
            up_file = st.file_uploader(
                "Sube un archivo de audio",
                type=["mp3", "wav", "m4a", "ogg", "mp4", "webm"],
                label_visibility="collapsed"
            )

            if up_file:
                st.audio(up_file)
                if st.button("Transcribir Archivo Subido", type="primary", use_container_width=True, key="btn_tr_file"):
                    data = up_file.getvalue()
                    with st.spinner("Transcribiendo archivo con Whisper…"):
                        try:
                            texto, es_demo = transcribe_audio(data, up_file.name)
                        except Exception as e:
                            texto, es_demo = f"Error en transcripción: {str(e)[:250]}", DEMO
                    
                    import uuid
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
            st.markdown("### Resultados de Transcripción")
        with header_col2:
            if st.session_state.transcripciones:
                if st.button("Limpiar Historial", key="btn_clear_audios", use_container_width=True):
                    st.session_state.transcripciones = []
                    st.rerun()

        if not st.session_state.transcripciones:
            render_html("""
            <div class="sa-empty-state">
              <div style="width:52px; height:52px; margin:0 auto 12px auto; border-radius:14px; background:linear-gradient(135deg, rgba(245,158,11,0.25) 0%, rgba(217,119,6,0.1) 100%); border:1.5px solid rgba(245,158,11,0.45); color:#FDE68A; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px rgba(245,158,11,0.2);">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="23"></line>
                  <line x1="8" y1="23" x2="16" y2="23"></line>
                </svg>
              </div>
              <h4 style="font-weight:800; color:#FFFFFF; font-size:1.1rem; margin:0 0 6px 0;">No hay transcripciones recientes</h4>
              <p style="color:#94A3B8; font-size:0.88rem; margin:0;">Grabe su voz con el micrófono o suba un archivo de audio para transcribir.</p>
            </div>
            """)
        else:
            for idx, item in enumerate(st.session_state.transcripciones):
                item_id = item.get("id", f"{idx}_{item.get('hora', '')}")
                tag_badge = (
                    '<span style="padding:3px 10px; border-radius:9999px; font-size:0.72rem; font-weight:800; background:rgba(245,158,11,0.18); color:#FBBF24; border:1px solid rgba(245,158,11,0.4);">MODO DEMO</span>'
                    if item["demo"] else
                    '<span style="padding:3px 10px; border-radius:9999px; font-size:0.72rem; font-weight:800; background:rgba(16,185,129,0.18); color:#34D399; border:1px solid rgba(16,185,129,0.4);">WHISPER-1</span>'
                )
                
                render_html(f"""
                <div class="sa-card" style="margin-bottom:0.75rem;">
                  <div style="display:flex; justify-content:space-between; align-items:center; padding-bottom:0.5rem; margin-bottom:0.5rem; border-bottom:1px solid #1F2937;">
                    <span style="font-weight:800; color:#FFFFFF; font-size:0.92rem;">{item['archivo']}</span>
                    <div>{tag_badge}</div>
                  </div>
                </div>
                """)
                
                st.text_area("Texto Transcrito:", value=item["texto"], height=95, key=f"tx_area_{item_id}")
                
                c_act1, c_act2 = st.columns([1.5, 1])
                with c_act1:
                    if st.button("Enviar al Gestor como Solicitud de Préstamo", key=f"btn_send_{item_id}", type="primary", use_container_width=True):
                        process_assistant_message(f"Procesa esta solicitud de préstamo dictada por audio: {item['texto'][:350]}")
                with c_act2:
                    st.download_button(
                        "Descargar TXT",
                        data=item["texto"],
                        file_name=f"transcripcion_{item['archivo']}.txt",
                        mime="text/plain",
                        key=f"dl_{item_id}",
                        use_container_width=True
                    )


# ==============================================================================
# TAB 3: GESTOR READOUT / ASISTENTE DE PRODUCTIVIDAD (OPENAI ASSISTANTS)
# ==============================================================================
with tab_asist:
    render_html("""
    <div style="margin-bottom:1.25rem;">
      <h2 style="font-size:1.6rem; font-weight:800; margin:0; color:#FFFFFF; font-family:'Fraunces',serif;">Gestor Bibliotecario Readout</h2>
      <p style="color:#94A3B8; font-size:0.9rem; margin:4px 0 0 0;">Implementación de <strong>OpenAI Assistants API</strong> bajo scripting. Orquesta <strong>Threads</strong>, <strong>Runs</strong> y <strong>Function Calling</strong> para interactuar con Email (SMTP), Google Sheets / Readout y WhatsApp (WAHA).</p>
    </div>
    """)

    col_chat_asist, col_tools = st.columns([1.2, 0.8], gap="large")

    with col_chat_asist:
        st.markdown("### Terminal del Gestor")
        st.markdown("<p style='font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#94A3B8; margin-bottom:0.6rem;'>SUGERENCIAS DE GESTIÓN READOUT:</p>", unsafe_allow_html=True)
        
        ca1, ca2 = st.columns(2)
        with ca1:
            if st.button("Emitir boleta de préstamo por Email", key="cmd_email", use_container_width=True):
                process_assistant_message("Envía un correo de confirmación de préstamo de Clean Code a lector@universidad.edu.pe con plazo de 7 días.")
        with ca2:
            if st.button("Registrar préstamo en Sheets / Readout", key="cmd_sheet", use_container_width=True):
                process_assistant_message("Registra un préstamo de 2 ejemplares de Inteligencia Artificial y 1 Quijote con una fianza total de 50 soles.")

        # Chat del asistente con scroll independiente
        with st.container(height=480, border=True):
            if not st.session_state.asist_msgs:
                render_html("""
                <div class="sa-empty-state" style="margin-top:1.5rem;">
                  <div style="width:52px; height:52px; margin:0 auto 12px auto; border-radius:14px; background:linear-gradient(135deg, rgba(16,185,129,0.25) 0%, rgba(5,150,105,0.1) 100%); border:1.5px solid rgba(16,185,129,0.45); color:#A7F3D0; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px rgba(16,185,129,0.2);">
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                    </svg>
                  </div>
                  <h4 style="font-weight:800; color:#FFFFFF; font-size:1.05rem; margin:0 0 6px 0;">Gestor listo para ejecutar acciones</h4>
                  <p style="color:#94A3B8; font-size:0.88rem; margin:0; line-height:1.5;">Pídale registrar préstamos, gestionar reservas de sala de lectura o enviar recordatorios por WhatsApp.</p>
                </div>
                """)
            else:
                for m in st.session_state.asist_msgs:
                    with st.chat_message(m["role"]):
                        st.markdown(m["content"])
                        if "actions" in m:
                            for act in m["actions"]:
                                render_html(f'<span style="display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:8px; font-size:0.75rem; font-weight:700; background:rgba(16,185,129,0.18); color:#34D399; border:1px solid rgba(16,185,129,0.4); margin:4px 0;"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>{act}</span>')

        # Si hay un borrador pendiente de confirmación en el asistente
        if st.session_state.asist_msgs:
            last_as_msg = next((m.get("content", "") for m in reversed(st.session_state.asist_msgs) if m.get("role") == "assistant"), "")
            if "Borrador de Solicitud" in last_as_msg or "Borrador de tu Solicitud" in last_as_msg or "Confirmación Requerida" in last_as_msg:
                col_ac1, col_ac2 = st.columns([1.5, 1])
                with col_ac1:
                    if st.button("Confirmar Operación", type="primary", use_container_width=True, key="btn_confirm_asist"):
                        process_assistant_message("Sí, confirmar")
                with col_ac2:
                    if st.button("Modificar Datos", use_container_width=True, key="btn_modify_asist"):
                        process_assistant_message("Deseo modificar mi solicitud")

        asist_input = st.chat_input("Pida una acción: registrar préstamo, emitir boleta, notificar por WhatsApp…", key="asist_chat_box")
        if asist_input:
            process_assistant_message(asist_input)

    with col_tools:
        st.markdown("### Disparo Directo de Herramientas")
        st.caption("Prueba individual de cada conector de Function Calling:")

        tool_tab1, tool_tab2, tool_tab3 = st.tabs(["Email (SMTP)", "Google Sheets / Readout", "WhatsApp"])

        with tool_tab1:
            st.markdown("#### Enviar Boleta por Correo")
            to_email = st.text_input("Destinatario", "usuario@gmail.com", key="dir_email_to")
            sub_email = st.text_input("Asunto", "Confirmación de Préstamo de Libros · Readout", key="dir_email_sub")
            body_email = st.text_area("Cuerpo del Correo", "Hola, confirmamos su préstamo de 1x Clean Code por 7 días. Código de Ticket Readout: RO-2026-0925.", key="dir_email_body", height=85)
            if st.button("Ejecutar send_email()", type="primary", use_container_width=True, key="btn_dir_email"):
                res = send_email(to_email, sub_email, body_email)
                if res.get("ok"):
                    st.success(f"Ejecución exitosa: {res.get('detail')}")
                else:
                    st.warning(f"Resultado: {res.get('detail')}")

        with tool_tab2:
            st.markdown("#### Registrar en Base / Readout")
            tipo_sheet = st.selectbox("Tipo de Registro", ["prestamo", "reserva", "devolucion", "incidencia"], key="dir_sheet_tipo")
            det_sheet = st.text_input("Detalle de Libros", "1x Clean Code + 1x Cien Años de Soledad", key="dir_sheet_det")
            mon_sheet = st.text_input("Fianza / Arancel (S/)", "25.00", key="dir_sheet_mon")
            if st.button("Ejecutar log_to_sheet()", type="primary", use_container_width=True, key="btn_dir_sheet"):
                res = log_to_sheet(tipo_sheet, det_sheet, mon_sheet, "")
                if res.get("ok"):
                    st.success(f"Ejecución exitosa: {res.get('detail')}")
                else:
                    st.warning(f"Resultado: {res.get('detail')}")

        with tool_tab3:
            st.markdown("#### Enviar Recordatorio WhatsApp")
            w_to = st.text_input("Número de Teléfono / WhatsApp (ej. 987509272 o 51987509272@c.us)", "987509272", key="dir_wsp_to")
            w_msg = st.text_area("Mensaje", "Hola, su préstamo en Readout ha sido registrado. Recuerde devolver los ejemplares antes de la fecha límite.", key="dir_wsp_msg", height=85)
            if st.button("Ejecutar send_whatsapp()", type="primary", use_container_width=True, key="btn_dir_wsp"):
                res = send_whatsapp(w_to, w_msg)
                if res.get("ok"):
                    st.success(f"Ejecución exitosa: {res.get('detail')}")
                else:
                    st.warning(f"Resultado: {res.get('detail')}")


# ==============================================================================
# TAB 4: AUDITORÍA & LOGS DE OPERACIÓN
# ==============================================================================
with tab_logs:
    render_html("""
    <div style="margin-bottom:1.25rem;">
      <h2 style="font-size:1.6rem; font-weight:800; margin:0; color:#FFFFFF; font-family:'Fraunces',serif;">Centro de Auditoría & Logs en Tiempo Real</h2>
      <p style="color:#94A3B8; font-size:0.9rem; margin:4px 0 0 0;">Registro histórico persistente de todas las automatizaciones de préstamos disparadas por el Asistente y las herramientas de Function Calling.</p>
    </div>
    """)

    log_sub1, log_sub2, log_sub3 = st.tabs(["Correos Electrónicos", "Hojas de Cálculo Readout CSV", "WhatsApp Logs"])
    data_dir = Path("data")

    with log_sub1:
        email_file = data_dir / "email_log.jsonl"
        if email_file.exists():
            lines = [line for line in email_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                st.markdown(f"**Total de envíos registrados:** `{len(lines)}`")
                for line in reversed(lines[-15:]):
                    try:
                        record = json.loads(line)
                        mode_badge = (
                            '<span style="padding:3px 8px; border-radius:6px; font-size:0.72rem; font-weight:800; background:rgba(59,130,246,0.18); color:#60A5FA; border:1px solid rgba(59,130,246,0.4);">SMTP REAL</span>'
                            if record.get('mode') == 'smtp' else
                            '<span style="padding:3px 8px; border-radius:6px; font-size:0.72rem; font-weight:800; background:rgba(245,158,11,0.18); color:#FBBF24; border:1px solid rgba(245,158,11,0.4);">DEMO SIMULADO</span>'
                        )
                        render_html(f"""
                        <div class="sa-card">
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span style="font-weight:800; color:#FFFFFF; font-size:0.92rem;">Para: {record.get('to')}</span>
                            <div>{mode_badge}</div>
                          </div>
                          <div style="font-size:0.85rem; font-weight:700; color:#CBD5E1; margin-bottom:8px;">Asunto: {record.get('subject')}</div>
                          <div class="sa-card-subtle-box" style="font-size:0.82rem; font-family:'JetBrains Mono',monospace; line-height:1.5;">{record.get('body')}</div>
                          <div style="text-align:right; font-size:0.72rem; color:#94A3B8; margin-top:6px;">{record.get('at')}</div>
                        </div>
                        """)
                    except Exception:
                        st.code(line)
            else:
                st.info("Aún no se han registrado correos. Realice una prueba en la pestaña Gestor Readout.")
        else:
            st.info("Aún no se ha generado el archivo de log de correos.")

    with log_sub2:
        sheet_file = data_dir / "sheets_log.csv"
        if sheet_file.exists():
            content = sheet_file.read_text(encoding="utf-8").strip()
            if content:
                rows = list(csv.DictReader(content.splitlines()))
                if rows:
                    st.markdown(f"**Total de registros de préstamos:** `{len(rows)}`")
                    st.dataframe(rows[::-1], use_container_width=True)
                    
                    st.download_button(
                        "Descargar Registro CSV Completo",
                        data=content,
                        file_name="sheets_log.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("La hoja está vacía por el momento.")
            else:
                st.info("El archivo CSV no contiene registros.")
        else:
            st.info("Aún no se ha generado el archivo CSV de registros.")

    with log_sub3:
        wsp_file = data_dir / "whatsapp_log.jsonl"
        if wsp_file.exists():
            lines = [line for line in wsp_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                st.markdown(f"**Total de mensajes enviados:** `{len(lines)}`")
                for line in reversed(lines[-15:]):
                    try:
                        record = json.loads(line)
                        mode_badge = (
                            '<span style="padding:3px 8px; border-radius:6px; font-size:0.72rem; font-weight:800; background:rgba(16,185,129,0.18); color:#34D399; border:1px solid rgba(16,185,129,0.4);">WAHA REAL</span>'
                            if record.get('mode') == 'waha' else
                            '<span style="padding:3px 8px; border-radius:6px; font-size:0.72rem; font-weight:800; background:rgba(245,158,11,0.18); color:#FBBF24; border:1px solid rgba(245,158,11,0.4);">DEMO SIMULADO</span>'
                        )
                        render_html(f"""
                        <div class="sa-card">
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span style="font-weight:800; color:#FFFFFF; font-size:0.92rem;">Destino: {record.get('to')}</span>
                            <div>{mode_badge}</div>
                          </div>
                          <div style="font-size:0.85rem; color:#34D399; background:rgba(16,185,129,0.14); padding:10px 14px; border-radius:8px; border:1px solid rgba(16,185,129,0.3); margin-top:8px;">{record.get('message')}</div>
                          <div style="text-align:right; font-size:0.72rem; color:#94A3B8; margin-top:6px;">{record.get('at')}</div>
                        </div>
                        """)
                    except Exception:
                        st.code(line)
            else:
                st.info("Aún no hay mensajes de WhatsApp registrados.")
        else:
            st.info("Aún no se ha generado el archivo de log de WhatsApp.")