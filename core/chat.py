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
        resp = client.chat.completions.create(model=CHAT_MODEL, messages=full, temperature=0.7, max_tokens=650)
        return resp.choices[0].message.content or ""
    except Exception:
        # Fallback automático a simulación bibliográfica si no hay créditos en la API Key
        return demo_reply(last_user)


