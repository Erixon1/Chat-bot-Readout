"""Chat con GPT (Chat Completions) + fallback demo para Biblioteca Readout."""
from core.client import get_openai_client, load_prompt, CHAT_MODEL
from core.demo_data import demo_reply


def chat_reply(messages: list[dict]) -> str:
    client, is_demo = get_openai_client()
    system = load_prompt("system_biblioteca.md")
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if is_demo:
        return demo_reply(last_user)
    try:
        full = [{"role": "system", "content": system}] + messages
        # Límite amplio: los modelos de razonamiento (p. ej. gpt-oss) consumen parte del cupo antes de responder
        resp = client.chat.completions.create(model=CHAT_MODEL, messages=full, temperature=0.7, max_tokens=4096)
        choice = resp.choices[0]
        content = choice.message.content or ""
        if choice.finish_reason == "length":
            content += "\n\n*(La respuesta alcanzó el límite de extensión. Pida «continúa» para ver el resto.)*"
        return content
    except Exception:
        # Fallback automático a simulación bibliográfica si no hay créditos en la API Key
        return demo_reply(last_user)


