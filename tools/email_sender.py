"""Envío de email: SMTP real si hay credenciales, si no log simulado."""
import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "data" / "email_log.jsonl"


def send_email(to: str, subject: str, body: str) -> dict:
    host, user, pwd = os.getenv("SMTP_HOST", ""), os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", "")
    port = int(os.getenv("SMTP_PORT", "587") or 587)
    sender = os.getenv("SMTP_FROM", "") or user
    record = {"to": to, "subject": subject, "body": body[:2000],
              "at": datetime.now(timezone.utc).isoformat(), "mode": "demo"}
    if host and user and pwd and sender:
        try:
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = sender, to, subject
            msg.set_content(body)
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.starttls()
                clean_pwd = pwd.replace(" ", "") if "gmail" in host else pwd
                s.login(user, clean_pwd)
                s.send_message(msg)
            record["mode"] = "smtp"
        except Exception as e:
            record["mode"] = "smtp_error"
            record["error"] = str(e)[:500]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    if record["mode"] == "demo":
        return {"ok": True, "mode": "demo",
                "detail": f"Email SIMULADO a {to} ('{subject}'). Configura SMTP_HOST/USER/PASSWORD en .env para envío real. Registro en data/email_log.jsonl."}
    if record["mode"] == "smtp":
        return {"ok": True, "mode": "smtp", "detail": f"Email real enviado a {to} vía {host}."}
    return {"ok": False, "mode": "smtp_error",
            "detail": f"No se pudo enviar por SMTP: {record.get('error')}. Se guardó el intento en el log."}
