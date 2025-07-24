"""Aplicación FastAPI con endpoints utilizados por Twilio."""

import os
import json
from fastapi import FastAPI, Response, WebSocket

from .tts import speak
from . import stt # Sigue importando stt.py, que ahora procesará las transcripciones de Twilio

# Instancia principal de la aplicación FastAPI
app = FastAPI()


@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    """
    WebSocket que recibe eventos (incluidas las transcripciones) de Twilio.
    """
    await websocket.accept()

    call_id = "unknown-call"

    # El primer mensaje contiene metadatos de la llamada
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
        print(f"Error receiving initial WebSocket message or call_id: {e}")

    # Delegamos el procesamiento del stream al módulo stt
    await stt.process_stream(websocket, call_id)
    print(f"[{call_id}] WebSocket connection closed.")


@app.get("/health")
async def health() -> dict[str, str]:
    """Endpoint de verificación de salud utilizado por la plataforma."""
    return {"status": "ok"}


@app.post("/voice")
async def voice():
    """Endpoint invocado por Twilio al iniciar una llamada."""

    initial_greeting_text = "Hola"

    greeting_audio_url = None
    try:
        greeting_audio_url = await speak(initial_greeting_text)
    except Exception as e:
        print(f"Error generating TTS audio for greeting: {e}")

    websocket_url = os.environ.get(
        "TWILIO_WEBSOCKET_URL", "wss://insightia-production.up.railway.app/stt"
    )

    # Construimos dinámicamente la respuesta TwiML que Twilio reproducirá.
    # Usamos <Stream> con 'track="inbound_speech"' para que Twilio envíe las transcripciones.
    twiml_parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<Response>",
        "  <Start>",
        # 'track="inbound_speech"': Indica a Twilio que envíe transcripciones del audio entrante.
        # 'language="es-ES"': Especifica el idioma del reconocimiento de voz (ajústalo si es necesario, ej. 'es-MX').
        # 'speechModel="default"': El modelo de reconocimiento. 'enhanced' podría ser otra opción.
        f"    <Stream url='{websocket_url}' track='inbound_speech' language='es-ES' speechModel='default'>",
        "      <!-- Opcional: <Hints> puedes añadir palabras clave aquí para mejorar la precisión del STT de Twilio. Ej: <Hints>nombre de producto, servicio, consulta</Hints> -->",
        "    </Stream>",
        "  </Start>",
    ]

    if greeting_audio_url:
        twiml_parts.append(f"  <Play>{greeting_audio_url}</Play>")
    else:
        twiml_parts.append(f"  <Say>{initial_greeting_text}</Say>")

    # Se utiliza un <Pause> para mantener la llamada abierta y permitir que
    # el WebSocket reciba audio y transcripciones del usuario.
    twiml_parts.append("  <Pause length='8'/>")
    twiml_parts.append("</Response>")

    twiml = "".join(twiml_parts)
    print(f"Generated TwiML: {twiml}")
    return Response(content=twiml, media_type="text/xml")
