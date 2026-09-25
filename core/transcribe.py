"""Transcripción de audio: Whisper real o demo simulada."""
from core.client import get_openai_client, WHISPER_MODEL
from core.demo_data import SAMPLE_AUDIO_TRANSCRIPTS

def transcribe_audio(file_bytes: bytes, filename: str) -> tuple[str, bool]:
    """Devuelve (texto, es_demo)."""
    client, is_demo = get_openai_client()
    if is_demo:
        for k, text in SAMPLE_AUDIO_TRANSCRIPTS.items():
            if k in filename.lower() or filename.lower() in k:
                return text, True
        return (
            f"[MODO DEMO — {filename}] Transcripción simulada:\n"
            "\"Solicitud de préstamo bibliotecario: Deseo solicitar 1 ejemplar de Clean Code de Robert Martin y 1 ejemplar de Inteligencia Artificial de Russell y Norvig por 7 días. "
            "Por favor confirmar al correo usuario@gmail.com y notificar al WhatsApp 987509272. Fianza total de S/ 35.00.\"",
            True,
        )
    try:
        import io
        buf = io.BytesIO(file_bytes)
        buf.name = filename if filename else "audio.mp3"
        resp = client.audio.transcriptions.create(model=WHISPER_MODEL, file=buf, language="es")
        texto_final = (resp.text or "").strip()
        if not texto_final:
            texto_final = "(Audio procesado: no se detectó voz o contenido hablado claro en la grabación)."
        return texto_final, False
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "quota" in err_str or "credit_balance" in err_str:
            for k, text in SAMPLE_AUDIO_TRANSCRIPTS.items():
                if k in filename.lower() or filename.lower() in k:
                    return text, True
            return (
                f"[MODO DEMO — {filename}] Transcripción simulada:\n"
                "\"Solicitud de préstamo bibliotecario: Deseo solicitar 1 ejemplar de Clean Code de Robert Martin y 1 ejemplar de Inteligencia Artificial de Russell y Norvig por 7 días. "
                "Por favor confirmar al correo usuario@gmail.com y notificar al WhatsApp 987509272. Fianza total de S/ 35.00.\"",
                True,
            )
        return f"Error en transcripción ({err_str[:200]})", False



