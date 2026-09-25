"""Cliente OpenAI en modo dual: REAL si hay OPENAI_API_KEY, DEMO si no."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
WHISPER_MODEL = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")
ASSISTANT_MODEL = os.getenv("OPENAI_ASSISTANT_MODEL", "gpt-4o-mini")

def get_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or "").strip().strip('"').strip("'")

def get_base_url() -> str | None:
    url = (os.getenv("OPENAI_BASE_URL") or "").strip().strip('"').strip("'")
    return url if url else None

def is_demo_mode() -> bool:
    mock_val = (os.getenv("FORCE_MOCK_MODE") or os.getenv("MOCK_MODE") or os.getenv("DEMO_MODE") or "").strip().lower()
    if mock_val in ("true", "1", "yes", "si", "on"):
        return True
    return not get_api_key()

def get_openai_client():
    """Devuelve (client, es_demo). client es None en modo demo."""
    if is_demo_mode():
        return None, True
    from openai import OpenAI
    base_url = get_base_url()
    if base_url:
        return OpenAI(api_key=get_api_key(), base_url=base_url), False
    return OpenAI(api_key=get_api_key()), False

def load_prompt(name: str) -> str:
    p = Path(__file__).resolve().parent.parent / "prompts" / name
    return p.read_text(encoding="utf-8").strip()
