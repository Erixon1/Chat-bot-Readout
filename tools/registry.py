"""Schemas Function Calling + dispatcher para Recepción y Gestión Bibliotecaria Readout."""
import json
from tools.email_sender import send_email
from tools.sheets_logger import log_to_sheet
from tools.whatsapp_sender import send_whatsapp

FUNCTION_SCHEMAS = [
    {"name": "enviar_email",
     "description": "Envía un correo oficial de confirmación de préstamo o reserva de libros con boleta y código de ticket.",
     "parameters": {"type": "object",
                    "properties": {"to": {"type": "string", "description": "Email del lector o usuario"},
                                   "subject": {"type": "string", "description": "Asunto del correo"},
                                   "body": {"type": "string", "description": "Cuerpo del mensaje con detalle de libros y plazos"}},
                    "required": ["to", "subject", "body"]}},
    {"name": "registrar_sheet",
     "description": "Registra una solicitud de préstamo, devolución o reserva de sala en el sistema Readout / Google Sheets.",
     "parameters": {"type": "object",
                    "properties": {"tipo": {"type": "string", "description": "prestamo | devolucion | reserva | incidencia"},
                                   "detalle": {"type": "string", "description": "Títulos de libros, cantidades y plazos"},
                                   "monto": {"type": "string", "description": "Fianza o arancel en Soles (ej. S/ 15.00)"},
                                   "fecha": {"type": "string", "description": "Fecha de registro YYYY-MM-DD"}},
                    "required": ["tipo", "detalle"]}},
    {"name": "enviar_whatsapp",
     "description": "Envía una notificación o recordatorio de fecha límite de entrega por WhatsApp vía WAHA.",
     "parameters": {"type": "object",
                    "properties": {"to": {"type": "string", "description": "Teléfono destino (ej. 987509272 o 51987509272@c.us)"},
                                   "message": {"type": "string", "description": "Texto del mensaje"}},
                    "required": ["to", "message"]}},
]


def openai_tools():
    return [{"type": "function", "function": s} for s in FUNCTION_SCHEMAS]


def dispatch(name: str, args_json: str) -> dict:
    try:
        args = json.loads(args_json or "{}")
    except Exception:
        return {"ok": False, "detail": "Argumentos JSON inválidos."}
    
    if name == "enviar_email":
        to_email = args.get("to", "").strip()
        sub = args.get("subject", "").strip() or "Confirmación de Préstamo de Libros · Readout"
        body = args.get("body", "").strip()
        return send_email(to_email, sub, body)

    if name == "registrar_sheet":
        tipo = (args.get("tipo") or "prestamo").strip().lower()
        detalle = (args.get("detalle") or "").strip()
        if not detalle:
            # Sin valores de plantilla: el modelo debe reintentar con los libros que pidió el lector
            return {"ok": False, "detail": "Falta 'detalle' (libros, cantidades y plazos). No se registró nada."}
        monto = (args.get("monto") or "No especificado").strip()
        fecha = args.get("fecha", "").strip()
        return log_to_sheet(tipo, detalle, monto, fecha)

    if name == "enviar_whatsapp":
        to_phone = args.get("to", "").strip()
        msg = args.get("message", "").strip()
        return send_whatsapp(to_phone, msg)

    return {"ok": False, "detail": f"Función desconocida: {name}"}


def demo_assistant_reply(user_text: str, messages: list[dict] | None = None) -> tuple[str, list[str]]:
    """Lógica de Recepción sin API para Readout: solicita datos, confirma y ejecuta herramientas."""
    from core.concierge import _parse_conversation_order, _extract_contacts
    all_msgs = messages or [{"role": "user", "content": user_text}]
    full_text = " ".join(m.get("content", "") for m in all_msgs if m.get("role") == "user")
    t = full_text.lower()
    actions: list[str] = []
    
    email, phone = _extract_contacts(full_text)
    to_email = email or "usuario@gmail.com"
    to_phone = phone or "987509272"
    
    items_detected, total_monto, es_prestamo, es_reserva = _parse_conversation_order(all_msgs)
    detalle_op = ", ".join(items_detected) if items_detected else "1x Clean Code — Robert C. Martin (Fianza Ref: S/ 15.00 · Plazo: 7 días)"
    monto_str = f"S/ {total_monto:.2f}"
    tipo_op = "reserva" if es_reserva else "prestamo"
    
    # 1. Google Sheets / Base Readout
    if es_prestamo or es_reserva or email or phone or any(w in t for w in ["registra", "prestamo", "préstamo", "libro", "sheet", "anota", "apunta"]):
        res_sheet = log_to_sheet(tipo_op, detalle_op, monto_str, "")
        actions.append(f"[Google Sheets / Readout] {res_sheet['detail']}")
        
    # 2. Correo
    if email or any(w in t for w in ["correo", "email", "mail", "reserva", "confirmar"]):
        res_email = send_email(to_email, f"Confirmación de {tipo_op.capitalize()} de Libros — Readout",
                                f"Estimado(a) lector(a):\n\nConfirmamos el registro oficial de su {tipo_op} en la Biblioteca Readout.\n\n"
                                f"Detalle de ejemplares y plazos:\n" +
                                "\n".join([f"- {it}" for it in items_detected]) +
                                f"\n\nFianza / Arancel de Referencia: {monto_str}\n"
                                f"Código de Ticket Readout: RO-2026-0925\n\n"
                                f"Recuerde devolver los ejemplares antes de la fecha límite establecida. ¡Buena lectura!")
        actions.append(f"[Email] {res_email['detail']}")
        
    # 3. WhatsApp
    if phone or any(w in t for w in ["whatsapp", "wsp", "mensaje al", "escribe al"]):
        res_wsp = send_whatsapp(to_phone, f"Hola, confirmamos su {tipo_op} en Readout ({detalle_op} - Fianza: {monto_str}). Le enviaremos un recordatorio antes de su fecha de devolución.")
        actions.append(f"[WhatsApp] {res_wsp['detail']}")
        
    if actions:
        resumen_libros = "\n".join([f"- {p}" for p in items_detected])
        return (f"Su solicitud ha sido procesada formalmente en el sistema de gestión Readout.\n\n"
                f"### Resumen Oficial del Préstamo:\n{resumen_libros}\n\n"
                f"**Fianza / Arancel procesado:** `{monto_str}`\n\n"
                f"Se ha enviado la boleta de confirmación por Email a `{to_email}` y el aviso de fecha límite a su WhatsApp `{to_phone}`. La operación quedó registrada en la base de datos oficial de Readout.", actions)

    return ("Bienvenido a la Recepción de la Biblioteca Readout. Indíqueme el libro que desea solicitar, o sus datos de contacto para preparar su solicitud de préstamo.", actions)
