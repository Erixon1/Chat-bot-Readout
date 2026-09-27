"""Gestor de Préstamos Readout: Chat Completions + Function Calling (compatible con OpenAI y Groq) + fallback demo.

Nota: la API de Assistants (threads/runs) no existe en Groq, por eso el ciclo de herramientas
se implementa directamente sobre Chat Completions.
"""
import json
from datetime import datetime
from core.client import get_openai_client, load_prompt, ASSISTANT_MODEL
from tools.registry import openai_tools, dispatch, demo_assistant_reply

MAX_TOOL_ROUNDS = 5
MAX_GENERATION_RETRIES = 3
TRUNCATION_NOTICE = "\n\n*(La respuesta alcanzó el límite de extensión. Pida «continúa» para ver el resto.)*"


def _is_malformed_generation(e: Exception) -> bool:
    """Groq devuelve 400 'Parsing failed' / tool_use_failed cuando el modelo emite una llamada a herramienta mal formada.
    Es intermitente: repetir la misma petición suele funcionar."""
    text = str(e)
    return getattr(e, "status_code", None) == 400 and (
        "failed_generation" in text or "tool_use_failed" in text or "Parsing failed" in text
    )


def model_error_message(e: Exception) -> str:
    """Mensaje para el lector cuando la llamada al modelo falla antes de ejecutar cualquier herramienta."""
    if _is_malformed_generation(e):
        return (f"El modelo generó una respuesta inválida {MAX_GENERATION_RETRIES} veces seguidas (falla intermitente del proveedor). "
                "No se ejecutó ninguna acción; vuelva a enviar su mensaje.")
    return f"No se pudo contactar al modelo ({type(e).__name__}: {str(e)[:200]}). No se ejecutó ninguna acción."


def _create_with_retry(client, **kwargs):
    """Una llamada al modelo con reintentos ante generaciones mal formadas.
    Es seguro reintentar: la petición fallida no ejecutó ninguna herramienta."""
    for attempt in range(MAX_GENERATION_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            if not _is_malformed_generation(e) or attempt == MAX_GENERATION_RETRIES - 1:
                raise


def run_with_tools(client, model: str, system: str, messages: list[dict], temperature: float = 0.5) -> tuple[str, list[str]]:
    """Ejecuta el ciclo modelo -> herramientas -> modelo hasta obtener una respuesta final.

    Devuelve (respuesta_final, acciones_ejecutadas). Los resultados reales de cada herramienta
    se devuelven al modelo para que redacte el resumen a partir de lo que efectivamente ocurrió.
    """
    system_full = f"{system}\n\nFecha actual: {datetime.now().strftime('%Y-%m-%d')}"
    convo: list[dict] = [{"role": "system", "content": system_full}]
    convo += [{"role": m["role"], "content": m["content"]}
              for m in messages if m.get("role") in ("user", "assistant") and m.get("content")]
    actions: list[str] = []

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            resp = _create_with_retry(
                client,
                model=model,
                messages=convo,
                tools=openai_tools(),
                tool_choice="auto",
                temperature=temperature,
                # Límite amplio: los modelos de razonamiento (p. ej. gpt-oss) consumen parte del cupo antes de responder
                max_tokens=4096,
            )
        except Exception as e:
            if not actions:
                raise
            # Ya se ejecutaron herramientas en rondas previas: no se debe afirmar que no pasó nada
            return (f"Las acciones de abajo **sí se ejecutaron**, pero el modelo falló al redactar el resumen "
                    f"({type(e).__name__}). No repita la solicitud para evitar registros o envíos duplicados.", actions)
        choice = resp.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            content = msg.content or ""
            if choice.finish_reason == "length":
                content += TRUNCATION_NOTICE
            return content, actions

        # Se reconstruye el mensaje a mano: algunos proveedores rechazan campos extra (p. ej. "reasoning")
        convo.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                           for tc in msg.tool_calls],
        })
        for tc in msg.tool_calls:
            result = dispatch(tc.function.name, tc.function.arguments)
            actions.append(f"[{tc.function.name}] {result.get('detail', 'Ejecutado')}")
            convo.append({"role": "tool", "tool_call_id": tc.id,
                          "content": json.dumps(result, ensure_ascii=False)[:3000]})

    return ("Se ejecutaron las acciones indicadas, pero el modelo no emitió un resumen final. "
            "Revise el detalle de acciones debajo de este mensaje.", actions)


def chat_with_assistant(user_text: str, thread_id: str | None = None, messages: list[dict] | None = None) -> tuple[str, str | None, list[str]]:
    """Devuelve (respuesta_final, thread_id, acciones_ejecutadas).

    thread_id se conserva por compatibilidad con app.py; el historial viaja completo en `messages`.
    """
    client, is_demo = get_openai_client()
    history = messages or [{"role": "user", "content": user_text}]
    if is_demo:
        reply, actions = demo_assistant_reply(user_text, history)
        return reply, thread_id, actions
    try:
        system = load_prompt("assistant_instructions.md")
        reply, actions = run_with_tools(client, ASSISTANT_MODEL, system, history)
        return reply, thread_id, actions
    except Exception as e:
        # Sin fallback demo en modo real: la demo ejecuta envíos reales con datos de plantilla
        return model_error_message(e), thread_id, []
