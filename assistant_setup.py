"""Crea el Asistente por scripting (CI/CD friendly) e imprime el assistant_id.

Uso:
    python assistant_setup.py
    # copia el ID impreso a OPENAI_ASSISTANT_ID en tu .env
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.client import get_openai_client
from core.assistant import ensure_assistant

client, is_demo = get_openai_client()
if is_demo:
    print("MODO DEMO: define OPENAI_API_KEY en .env para crear el asistente real.")
    raise SystemExit(1)
aid = ensure_assistant(client)
print(f"ASSISTANT_ID={aid}")
print("Copia ese valor a OPENAI_ASSISTANT_ID en tu .env")
