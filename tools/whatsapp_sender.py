"""Envío WhatsApp vía WAHA real o log simulado."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

LOG = Path(__file__).resolve().parent.parent / "data" / "whatsapp_log.jsonl"


def format_whatsapp_chatid(to: str) -> str:
    """Normaliza números de teléfono al formato chatId requerido por WAHA (ej. 51987654321@c.us)."""
    clean = to.strip()
    if "@c.us" in clean or "@g.us" in clean:
        return clean
    # Extraer solo dígitos
    digits = "".join(ch for ch in clean if ch.isdigit())
    if not digits:
        return clean
    # Si es número móvil peruano de 9 dígitos que empieza con 9
    if len(digits) == 9 and digits.startswith("9"):
        digits = "51" + digits
    return f"{digits}@c.us"


def send_whatsapp(to: str, message: str) -> dict:
    base, session = os.getenv("WAHA_URL", "").strip().rstrip("/"), os.getenv("WAHA_SESSION", "default")
    api_key = os.getenv("WAHA_API_KEY", "").strip()
    
    formatted_to = format_whatsapp_chatid(to)
    record = {"to": formatted_to, "original_to": to, "message": message[:1500], "at": datetime.now(timezone.utc).isoformat(), "mode": "demo"}
    
    if base:
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["X-Api-Key"] = api_key
            r = requests.post(f"{base}/api/sendText",
                              json={"session": session, "chatId": formatted_to, "text": message},
                              headers=headers, timeout=20)
            record["mode"] = "waha" if r.ok else "waha_error"
            record["status"] = r.status_code
            record["resp"] = r.text[:500]
        except Exception as e:
            record["mode"] = "waha_error"
            record["error"] = str(e)[:500]
    
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    if record["mode"] == "demo":
        return {"ok": True, "mode": "demo",
                "detail": f"WhatsApp SIMULADO a {formatted_to}: '{message[:100]}...'. Configura WAHA_URL en .env para envío real."}
    if record["mode"] == "waha":
        return {"ok": True, "mode": "waha", "detail": f"WhatsApp real enviado exitosamente a {formatted_to} vía WAHA."}
    
    return {"ok": False, "mode": "waha_error",
            "detail": f"Error al enviar por WAHA a {formatted_to} ({record.get('status')}: {record.get('resp', record.get('error'))})."}

