"""Asistente OpenAI (Threads/Runs/Function Calling) + fallback demo.
"""
import json
import os
import time
from core.client import get_openai_client, load_prompt, ASSISTANT_MODEL
from tools.registry import openai_tools, dispatch, demo_assistant_reply


def ensure_assistant(client) -> str:
    """Crea o reutiliza el asistente vía scripting. Devuelve assistant_id."""
    preset = os.getenv("OPENAI_ASSISTANT_ID", "").strip()
    if preset:
        return preset
    instructions = load_prompt("assistant_instructions.md")
    assistant = client.beta.assistants.create(
        name="Readout Gestor Bibliotecario",
        instructions=instructions,
        model=ASSISTANT_MODEL,
        tools=openai_tools(),
    )
    return assistant.id


def chat_with_assistant(user_text: str, thread_id: str | None = None, messages: list[dict] | None = None) -> tuple[str, str | None, list[str]]:
    """Devuelve (respuesta_final, thread_id, acciones_ejecutadas)."""
    client, is_demo = get_openai_client()
    if is_demo:
        reply, actions = demo_assistant_reply(user_text, messages)
        return reply, thread_id, actions
    try:
        assistant_id = ensure_assistant(client)
        if not thread_id:
            thread_id = client.beta.threads.create().id
        client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_text)
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
        actions: list[str] = []
        for _ in range(60):  # ~2 min max
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run.status == "requires_action":
                for call in run.required_action.submit_tool_outputs.tool_calls:
                    result = dispatch(call.function.name, call.function.arguments)
                    actions.append(f"{call.function.name}: {result.get('detail', '')}")
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id, run_id=run.id,
                        tool_outputs=[{"tool_call_id": call.id,
                                       "output": json.dumps(result, ensure_ascii=False)[:3000]}])
                continue
            if run.status in ("completed", "failed", "cancelled", "expired"):
                break
            time.sleep(2)
        msgs = client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=1)
        text = ""
        if msgs.data and msgs.data[0].content:
            for part in msgs.data[0].content:
                if part.type == "text":
                    text += part.text.value
        return text.strip() or f"(Run terminó en estado {run.status})", thread_id, actions
    except Exception:
        # Fallback a demo si la cuota de OpenAI está agotada
        reply, actions = demo_assistant_reply(user_text, messages)
        return reply, thread_id, actions


