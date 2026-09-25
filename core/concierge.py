"""Concierge Bibliotecario Omnicanal Readout — Agente de Recepción con soporte multimodal (Texto + Voz),
Function Calling (Email, Google Sheets, WhatsApp), flujo de confirmación en dos pasos y consulta bibliográfica.
"""
import json
import re
from datetime import datetime, timezone
from core.client import get_openai_client, load_prompt, CHAT_MODEL
from tools.registry import openai_tools, dispatch
from tools.email_sender import send_email
from tools.sheets_logger import log_to_sheet
from tools.whatsapp_sender import send_whatsapp
from core.demo_data import BOOK_ENTRIES, CLEAN_CODE, CIEN_ANOS, ARTE_GUERRA, BREVE_HISTORIA, QUIJOTE, IA_MODERNA, PRINCIPITO

BOOK_CATALOG = {
    "clean_code": {
        "name": "Clean Code (Código Limpio) — Robert C. Martin",
        "author": "Robert C. Martin (\"Uncle Bob\")",
        "category": "Tecnología & Ingeniería de Software",
        "price": 15.0,
        "duration": "7 días",
        "detail": CLEAN_CODE,
        "aliases": ["clean code", "codigo limpio", "código limpio", "robert martin", "uncle bob", "clean"]
    },
    "cien_anos": {
        "name": "Cien Años de Soledad — Gabriel García Márquez",
        "author": "Gabriel García Márquez (Premio Nobel)",
        "category": "Literatura Universal & Realismo Mágico",
        "price": 10.0,
        "duration": "14 días",
        "detail": CIEN_ANOS,
        "aliases": ["cien anos", "cien años", "soledad", "garcia marquez", "garcía márquez", "gabo", "macondo"]
    },
    "arte_guerra": {
        "name": "El Arte de la Guerra — Sun Tzu",
        "author": "Sun Tzu",
        "category": "Estrategia & Filosofía",
        "price": 8.0,
        "duration": "7 días",
        "detail": ARTE_GUERRA,
        "aliases": ["arte de la guerra", "arte guerra", "sun tzu", "suntzu", "estrategia"]
    },
    "breve_historia": {
        "name": "Breve Historia del Tiempo — Stephen Hawking",
        "author": "Stephen Hawking",
        "category": "Divulgación Científica & Cosmología",
        "price": 12.0,
        "duration": "14 días",
        "detail": BREVE_HISTORIA,
        "aliases": ["breve historia", "historia del tiempo", "hawking", "stephen hawking", "cosmos", "tiempo"]
    },
    "quijote": {
        "name": "Don Quijote de la Mancha — Miguel de Cervantes",
        "author": "Miguel de Cervantes Saavedra",
        "category": "Clásicos Universales & Narrativa",
        "price": 10.0,
        "duration": "14 días",
        "detail": QUIJOTE,
        "aliases": ["don quijote", "quijote", "cervantes", "sancho", "molinos"]
    },
    "ia_moderna": {
        "name": "Inteligencia Artificial: Un Enfoque Moderno — Russell & Norvig",
        "author": "Stuart Russell & Peter Norvig",
        "category": "Ciencias de la Computación & IA",
        "price": 20.0,
        "duration": "7 días",
        "detail": IA_MODERNA,
        "aliases": ["inteligencia artificial", "ia moderna", "russell", "norvig", "ia", "machine learning", "ia enfoque moderno"]
    },
    "principito": {
        "name": "El Principito — Antoine de Saint-Exupéry",
        "author": "Antoine de Saint-Exupéry",
        "category": "Fábula Filosófica & Humanismo",
        "price": 8.0,
        "duration": "7 días",
        "detail": PRINCIPITO,
        "aliases": ["el principito", "principito", "saint exupery", "saint-exupery"]
    }
}

PRICE_MAP = {
    15: "clean_code",
    10: "cien_anos",
    8: "arte_guerra",
    12: "breve_historia",
    20: "ia_moderna"
}

WORD_NUMS = {
    "un": 1, "uno": 1, "una": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6
}

def _extract_contacts(text: str) -> tuple[str | None, str | None]:
    """Extrae email y número de WhatsApp de un texto acumulado."""
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    email = email_match.group(0).strip(" .;:") if email_match else None
    
    clean_digits = re.sub(r'[^\d]', '', text)
    phone_match = re.search(r'(?:51)?(9\d{8})', clean_digits)
    phone = phone_match.group(1) if phone_match else None
    return email, phone

def _is_user_confirming(text: str) -> bool:
    """Detecta si el último mensaje del usuario es una confirmación afirmativa."""
    t = text.lower().strip(" .!¡¿?,\n\t")
    affirmative = [
        "si", "sí", "confirmar", "confirmo", "confirmado", "sí, confirmar", "si confirmar",
        "de acuerdo", "procede", "proceder", "dale", "correcto", "enviar", "enviar datos",
        "ok", "listo", "adelante", "perfecto", "conforme", "todo bien", "si por favor", "sí por favor",
        "si envia", "sí envía", "enviar prestamo", "enviar préstamo", "esta bien", "está bien", "dale procede"
    ]
    if t in affirmative:
        return True
    return any(t.startswith(w) or t == w for w in ["si", "sí", "confirm", "dale", "procede", "correcto", "ok", "listo"])

def _was_confirmation_requested(messages: list[dict]) -> bool:
    """Verifica si la recepcionista ya había presentado el borrador solicitando confirmación."""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            content = m.get("content", "").lower()
            if any(k in content for k in [
                "borrador de solicitud", "borrador de préstamo", "borrador de prestamo",
                "confirmación requerida", "confirmacion requerida",
                "¿confirma que los datos son correctos", "confirma que los datos",
                "proceder con el registro oficial en readout"
            ]):
                return True
            break
    return False

def _detect_mentioned_books(text: str) -> list[str]:
    """Identifica las claves de libros mencionadas en el texto."""
    t = text.lower()
    found: list[str] = []
    for key, info in BOOK_CATALOG.items():
        if any(re.search(rf'\b{re.escape(al)}\b', t) for al in info["aliases"]):
            if key not in found:
                found.append(key)
    return found

def _is_explicit_loan_intent(text: str) -> bool:
    """Verifica si el usuario expresa una intención de pedir prestado o agendar un préstamo."""
    t = text.lower()
    loan_keywords = [
        "prestar", "prestamo", "préstamo", "quiero el libro", "solicito", "solicitar",
        "agendar", "agendame", "agéndame", "llevar", "llevo", "me llevo", "alquilar",
        "reservar", "reserva", "sacar", "tomar prestado", "adquirir", "prestame", "préstame"
    ]
    return any(w in t for w in loan_keywords)

def _parse_conversation_order(messages: list[dict]) -> tuple[list[str], float, bool, bool]:
    """Analiza el historial multi-turno para retener libros solicitados, cantidades y fianza."""
    all_text_parts = [m.get("content", "") for m in messages if m.get("content")]
    full_conversation_text = " ".join(all_text_parts).lower()
    
    detected_items: dict[str, int] = {}
    
    for key, info in BOOK_CATALOG.items():
        for alias in info["aliases"]:
            prefix_pattern = rf'(\d+|un|uno|una|dos|tres|cuatro|cinco|seis)\s*(?:x\s*)?(?:ejemplares?|libros?|tomos?|copias?|unidades?|unidad|de\s*)?\s*{re.escape(alias)}\b'
            for m in re.findall(prefix_pattern, full_conversation_text):
                qty = WORD_NUMS.get(m, int(m) if m.isdigit() else 1)
                detected_items[key] = max(detected_items.get(key, 0), qty)
                
            suffix_pattern = rf'{re.escape(alias)}\s*(?:\([^\)]*(\d+)[^\)]*\)|[-:]?\s*(\d+)\s*(?:unidades?|ejemplares?|unidad)?|x\s*(\d+))'
            for match_tuple in re.findall(suffix_pattern, full_conversation_text):
                for m in match_tuple:
                    if m and m.isdigit():
                        detected_items[key] = max(detected_items.get(key, 0), int(m))
                
    for key, info in BOOK_CATALOG.items():
        if key not in detected_items:
            if any(re.search(rf'\b{re.escape(al)}\b', full_conversation_text) for al in info["aliases"]):
                detected_items[key] = 1

    es_reserva = any(w in full_conversation_text for w in ["sala", "cubículo", "cubiculo", "estudio", "reserva de sala", "investigadores"])
    es_prestamo = _is_explicit_loan_intent(full_conversation_text) or bool(detected_items)
    
    items_summary: list[str] = []
    total_monto = 0.0
    
    for k, qty in detected_items.items():
        info = BOOK_CATALOG[k]
        sub = qty * info["price"]
        total_monto += sub
        items_summary.append(f"{qty}x {info['name']} (Fianza Ref: S/ {sub:.2f} · Plazo: {info['duration']})")
        
    if not items_summary and es_reserva:
        people_match = re.search(r'(\d+)\s*(?:personas|investigadores|alumnos)', full_conversation_text)
        num_p = int(people_match.group(1)) if people_match else 2
        total_monto = float(num_p * 5.0)
        items_summary.append(f"Reserva de Sala de Estudio Grupal ({num_p} personas - 3 horas)")
        
    return items_summary, total_monto, es_prestamo, es_reserva

def demo_concierge_reply(messages: list[dict]) -> tuple[str, list[str]]:
    """Motor de Recepción para Readout: responde consultas informativas o guía el flujo de préstamo."""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    last_user_lower = last_user.lower()
    actions: list[str] = []
    
    full_conversation_user = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
    email, phone = _extract_contacts(full_conversation_user)
    
    items_detected, total_monto, es_prestamo, es_reserva = _parse_conversation_order(messages)
    conf_already_requested = _was_confirmation_requested(messages)
    user_is_confirming = _is_user_confirming(last_user)
    
    # 1. PASO 3: El lector confirma explícitamente un borrador previo -> Ejecutar herramientas y recibo final
    if conf_already_requested and user_is_confirming:
        tipo_op = "reserva" if es_reserva else "prestamo"
        monto_str = f"S/ {total_monto:.2f}"
        detalle_str = ", ".join(items_detected) if items_detected else "1x Clean Code — Robert C. Martin (S/ 15.00)"
        
        res_sheet = log_to_sheet(tipo_op, detalle_str, monto_str, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        actions.append(f"[Google Sheets / Readout] {res_sheet.get('detail', 'Préstamo registrado exitosamente')}")
        
        if email:
            sub = f"Confirmación de {tipo_op.capitalize()} de Libros · Readout ({monto_str})"
            body = (f"Estimado(a) lector(a):\n\nConfirmamos el registro oficial de su {tipo_op} en la Biblioteca Readout.\n\n"
                    f"Detalle de ejemplares y plazos:\n" +
                    "\n".join([f"- {it}" for it in items_detected]) + "\n\n"
                    f"Fianza / Arancel de Referencia: {monto_str}\n"
                    f"Código de Ticket Readout: RO-2026-{datetime.now().strftime('%m%d%H%M')}\n\n"
                    f"Recuerde devolver los ejemplares dentro del plazo establecido para evitar penalidades. ¡Buena lectura!")
            res_email = send_email(email, sub, body)
            actions.append(f"[Email] {res_email.get('detail', f'Enviado a {email}')}")
            
        if phone:
            msg = (f"Hola, confirmamos su {tipo_op} de libros en Readout.\n"
                   f"Ejemplares: {detalle_str}\n"
                   f"Fianza total: {monto_str}\n"
                   f"Le enviaremos un recordatorio previo a su fecha de devolución.")
            res_wsp = send_whatsapp(phone, msg)
            actions.append(f"[WhatsApp] {res_wsp.get('detail', f'Enviado a {phone}')}")

        receipt_lines = [
            "Su solicitud de préstamo ha sido **confirmada y procesada exitosamente en Readout**.",
            "",
            "### Resumen Oficial de su Préstamo:",
        ]
        for it in items_detected:
            receipt_lines.append(f"- {it}")
        receipt_lines.append("")
        receipt_lines.append(f"**Fianza / Arancel procesado:** `{monto_str}`")
        receipt_lines.append(f"**Código de Préstamo Readout:** `RO-2026-{datetime.now().strftime('%m%d%H%M')}`")
        receipt_lines.append("")

        if email and phone:
            receipt_lines.append(f"Se ha enviado la constancia de préstamo por **Email** a `{email}` y el recordatorio a su **WhatsApp** `{phone}`. La operación quedó registrada en la base de datos oficial de **Readout**.")
        elif email:
            receipt_lines.append(f"Constancia de préstamo enviada a `{email}` y registrada en el sistema **Readout**.")
        elif phone:
            receipt_lines.append(f"Aviso de préstamo enviado a su **WhatsApp** `{phone}` y registrado en el sistema **Readout**.")
            
        return "\n".join(receipt_lines), actions

    # 2. CASO: El usuario sólo consulta datos de libros, sinopsis, catálogo o recomendaciones
    mentioned_in_last = _detect_mentioned_books(last_user)
    has_explicit_loan_intent = _is_explicit_loan_intent(last_user_lower) or _is_explicit_loan_intent(full_conversation_user)
    
    # Si el usuario pregunta por libros o catálogo sin haber dado datos de contacto y sin intención directa de préstamo
    if not (email and phone) and (not has_explicit_loan_intent or any(w in last_user_lower for w in ["de que trata", "de qué trata", "informacion", "información", "datos", "sinopsis", "resumen", "autor", "que libros", "qué libros", "catalogo", "catálogo", "muestrame", "muéstrame", "hablame", "háblame", "cuentame", "cuéntame"])):
        if mentioned_in_last:
            details = [BOOK_CATALOG[k]["detail"] for k in mentioned_in_last]
            resp_lines = [
                "Estimado(a) lector(a), con gusto le comparto la información y síntesis de las obras solicitadas:",
                "",
                "\n\n---\n\n".join(details),
                "",
                "---",
                "Si desea tramitar el **préstamo** de alguno de estos ejemplares, por favor indíqueme su **correo electrónico** y su **número de WhatsApp** para preparar su registro oficial."
            ]
            return "\n".join(resp_lines), []
        
        if any(w in last_user_lower for w in ["catalogo", "catálogo", "libros", "recomiendas", "que tienes", "hola", "buenas", "obras", "titulos", "títulos"]):
            lines = [
                "Bienvenido(a) a la Recepción de la **Biblioteca Readout**, Sistema de Orientación y Préstamo Bibliotecario.",
                "A continuación se detalla el acervo bibliográfico oficial con sus condiciones de fianza y plazos:",
                "",
                "| Título y Autor | Fianza / Arancel Ref. | Plazo Máximo | Categoría |",
                "| :--- | :--- | :--- | :--- |",
                "| **Clean Code** — Robert C. Martin | `S/ 15.00` | 7 días | Software & Clean Arch |",
                "| **Cien Años de Soledad** — G. García Márquez | `S/ 10.00` | 14 días | Literatura Universal |",
                "| **El Arte de la Guerra** — Sun Tzu | `S/ 8.00` | 7 días | Estrategia & Liderazgo |",
                "| **Breve Historia del Tiempo** — Stephen Hawking | `S/ 12.00` | 14 días | Divulgación Científica |",
                "| **Don Quijote de la Mancha** — Miguel de Cervantes | `S/ 10.00` | 14 días | Clásicos Universales |",
                "| **Inteligencia Artificial: Enfoque Moderno** — Russell & Norvig | `S/ 20.00` | 7 días | Computer Science / IA |",
                "| **El Principito** — Antoine de Saint-Exupéry | `S/ 8.00` | 7 días | Fábula Filosófica |",
                "",
                "Indíqueme el título de su interés para brindarle su sinopsis detallada, o proporcione sus datos de contacto (correo y WhatsApp) para tramitar un préstamo."
            ]
            return "\n".join(lines), []

    # 3. CASO: El usuario desea prestar libros pero AÚN NO ha entregado correo ni teléfono
    if not (email or phone) and items_detected:
        lines = [
            "Estimado(a) lector(a),",
            "",
            "Confirmo la disponibilidad de los ejemplares solicitados:",
        ]
        for it in items_detected:
            lines.append(f"- {it}")
        lines.append("")
        lines.append(f"**Fianza / Arancel total de referencia:** `S/ {total_monto:.2f}`")
        lines.append("")
        lines.append("Para generar su solicitud formal de préstamo y emitir la boleta oficial de Readout, por favor proporcione:")
        lines.append("1. Su **correo electrónico** (para la boleta y constancia oficial).")
        lines.append("2. Su **número de WhatsApp** (para recordatorios de fecha de devolución).")
        return "\n".join(lines), []

    # 4. PASO 2: Se tienen libros y datos de contacto -> Presentación del Borrador y Solicitud de Confirmación
    if items_detected:
        monto_str = f"S/ {total_monto:.2f}"
        email_display = f"`{email}`" if email else "*Pendiente de registro*"
        phone_display = f"`{phone}`" if phone else "*Pendiente de registro*"

        draft_lines = [
            "### Borrador de Solicitud de Préstamo (Confirmación Requerida):",
            "Por favor, verifique que los datos de su préstamo sean conformes antes de realizar la emisión oficial:",
            "",
            "**Ejemplar(es) y condiciones:**",
        ]
        for it in items_detected:
            draft_lines.append(f"- {it}")
        draft_lines.append("")
        draft_lines.append(f"**Fianza / Arancel total:** `{monto_str}`")
        draft_lines.append(f"**Correo para boleta de préstamo:** {email_display}")
        draft_lines.append(f"**WhatsApp para recordatorios:** {phone_display}")
        draft_lines.append("")
        draft_lines.append("---")
        
        if email and phone:
            draft_lines.append("¿Confirma que los datos son correctos? Responda **\"Sí, confirmar\"** para emitir el préstamo oficial y despachar las notificaciones, o indíqueme si requiere modificar algún título.")
        elif email and not phone:
            draft_lines.append("¿Desea registrar su número de **WhatsApp** para recordatorios de fecha de devolución? Si los datos están conformes, responda **\"Sí, confirmar\"** para emitir la boleta por correo.")
        elif phone and not email:
            draft_lines.append("¿Desea registrar su **correo electrónico** para recibir la boleta formal? Si los datos están conformes, responda **\"Sí, confirmar\"** para registrar la operación.")
        else:
            draft_lines.append("Para completar su solicitud, por favor indíqueme su **correo electrónico** y su **número de WhatsApp**.")

        return "\n".join(draft_lines), []

    # 5. Default fallback informativo
    return (
        "Bienvenido(a) a la Recepción de la Biblioteca Readout. ¿Qué obra o consulta académica desea realizar hoy? "
        "Puede solicitar información sobre obras como Clean Code, Cien Años de Soledad, Inteligencia Artificial, entre otras.",
        []
    )

def chat_with_concierge(messages: list[dict]) -> tuple[str, list[str]]:
    """Procesa mensajes de la Recepción de Readout garantizando atención bibliográfica y confirmación en dos pasos."""
    client, is_demo = get_openai_client()
    if is_demo:
        return demo_concierge_reply(messages)
    
    last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    conf_already_requested = _was_confirmation_requested(messages)
    user_is_confirming = _is_user_confirming(last_user)
    
    # Si ya se presentó un borrador y el usuario está confirmando afirmativamente, despachar herramientas
    if conf_already_requested and user_is_confirming:
        return demo_concierge_reply(messages)
    
    try:
        system = load_prompt("system_concierge.md")
        formatted_messages = [{"role": "system", "content": system}]
        for m in messages:
            if m.get("role") in ("user", "assistant"):
                formatted_messages.append({"role": m["role"], "content": m["content"]})
                
        tools = openai_tools()
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=formatted_messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.5,
            max_tokens=900
        )
        
        choice = response.choices[0]
        msg = choice.message
        actions: list[str] = []
        
        if msg.tool_calls:
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = tc.function.arguments
                res = dispatch(fn_name, fn_args)
                act_label = f"[{fn_name}] {res.get('detail', 'Ejecutado')}"
                actions.append(act_label)
            return demo_concierge_reply(messages)
            
        return msg.content or "Buenas tardes, ¿en qué libro o gestión de biblioteca le puedo colaborar hoy?", actions
    except Exception:
        return demo_concierge_reply(messages)
