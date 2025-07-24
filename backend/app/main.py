"""FastAPI application with endpoints used by Twilio."""

import os
import json  # Necesario para parsear el mensaje inicial del WebSocket
from fastapi import FastAPI, Response, WebSocket

from .tts import speak
from . import stt

# Instancia principal de la aplicación
app = FastAPI()


@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    """WebSocket que recibe audio de Twilio y envía las transcripciones."""

    # Aceptamos la conexión para empezar a recibir audio
    await websocket.accept()

    call_id = "unknown-call"

    # El primer mensaje contiene metadatos de la llamada; de ahí extraemos el
    # callSid para identificar la conversación.
    try:
        initial_message = await websocket.receive_json()
        print(
            "DEBUG: Initial WebSocket message from Twilio:"
            f" {json.dumps(initial_message, indent=2)}"
        )

        if initial_message.get("event") == "start":
            call_sid = initial_message.get("start", {}).get("callSid")
            if call_sid:
                call_id = call_sid
                print(f"[{call_id}] Received callSid: {call_id}")
    except Exception as e:
        # Si algo falla, continuamos con un identificador genérico
        print(f"Error receiving initial WebSocket message or call_id: {e}")

    # Delegamos el procesamiento del stream de audio
    await stt.process_stream(websocket, call_id)
    print(f"[{call_id}] WebSocket connection closed.")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint used by the platform."""
    return {"status": "ok"}


@app.post("/voice")
async def voice():
    """Endpoint invocado por Twilio al iniciar una llamada."""

    # Texto de bienvenida que se reproducirá al iniciarse la conversación
    initial_greeting_text = "Nuestra misión es compartir la belleza de las palabras y las historias que se tejen con ellas."

    greeting_audio_url = None
    try:
        greeting_audio_url = await speak(initial_greeting_text)
    except Exception as e:
        print(f"Error generating TTS audio for greeting: {e}")

    websocket_url = os.environ.get(
        "TWILIO_WEBSOCKET_URL", "wss://insightia-production.up.railway.app/stt"
    )

    # Construimos dinámicamente la respuesta TwiML que Twilio reproducirá
    twiml_parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<Response>",
        "  <Start>",
        f"    <Stream url='{websocket_url}' />",
        "  </Start>",
    ]

    if greeting_audio_url:
        # Si el audio se generó correctamente, lo reproducimos
        twiml_parts.append(f"  <Play>{greeting_audio_url}</Play>")
    else:
        # En caso contrario pronunciamos el texto directamente
        twiml_parts.append(f"  <Say>{initial_greeting_text}</Say>")

    # Mantener la llamada abierta mientras se reproduce el saludo. Se utiliza
    # un bloque <Pause> para que Twilio no finalice la llamada de inmediato y
    # podamos recibir audio del usuario por el WebSocket.
    twiml_parts.append("  <Pause length='20'/>")
    twiml_parts.append("</Response>")

    twiml = "".join(twiml_parts)
    print(f"Generated TwiML: {twiml}")  # Para depuración
    return Response(content=twiml, media_type="text/xml")
