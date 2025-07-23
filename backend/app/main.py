# backend/app/main.py
import os
from fastapi import FastAPI, Response, WebSocket
import json # Necesario para parsear el mensaje inicial del WebSocket

from .tts import speak
from . import stt, wer
print("--- DEPLOYMENT VERSION: 2025-07-22-v3 ---") # <--- AÑADE ESTA LÍNEA

app = FastAPI()

@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    await websocket.accept()
    call_id = None
    stream_sid = None

    try:
        # Bucle para asegurar que procesamos el mensaje 'start'
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                stream_sid = data.get("streamSid")
                call_id = data.get("start", {}).get("callSid")
                print(f"[{call_id}] Stream started via main.py. (StreamSid: {stream_sid})")
                break # Salimos del bucle una vez tenemos el call_id
            elif event == "connected":
                print("WebSocket connection reported as 'connected' by Twilio.")
            else:
                # Ignorar otros eventos como 'media' en esta fase
                print(f"Ignoring event '{event}' during init phase.")

        if not call_id:
            raise RuntimeError("Could not extract call_id from 'start' event.")

        # Ahora delegamos, pasando el WebSocket y el call_id
        await stt.process_stream(websocket, call_id)

    except Exception as e:
        print(f"!!! Error in websocket_stt handler: {e} !!!")
    finally:
        print(f"[{call_id or 'unknown'}] WebSocket handler in main.py finished.")

@app.post("/wer")
def calc_wer(payload: dict) -> dict:
    """Calcular WER entre referencia e hipótesis y registrar."""
    ref = payload.get("reference", "")
    hyp = payload.get("hypothesis", "")
    score = wer.wer(ref, hyp)
    wer.metrics.add(score)
    return {"wer": score}


@app.get("/metrics")
def metrics():
    """Obtener métricas de WER diarias."""
    return wer.metrics.metrics()


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint used by the platform."""
    return {"status": "ok"}
@app.post("/voice")
async def voice():
    """
    Devuelve TwiML que reproduce un saludo TTS y luego inicia una 
    conversación bidireccional continua a través de un WebSocket.
    """
    print("--- VOICE ENDPOINT TRIGGERED - VERSION 2025-07-22-FINAL-CHECK ---") # Nuevo log de verificación
    initial_greeting_text = "Nuestra misión es compartir la belleza de las palabras y las historias que se tejen con ellas. ¿Cómo puedo ayudarte hoy?"

    greeting_audio_url = None
    try:
        greeting_audio_url = await speak(initial_greeting_text)
    except Exception as e:
        print(f"Error generating TTS audio for greeting: {e}")

    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL", "wss://insightia-production.up.railway.app/stt")

    twiml_parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<Response>",
        "  <Start>",  # <-- CAMBIO
        f"    <Stream url='{websocket_url}' />",
        "  </Start>"  # <-- CAMBIO
    ]

    if greeting_audio_url:
        twiml_parts.append(f"  <Play>{greeting_audio_url}</Play>")
    else:
        twiml_parts.append(f"  <Say>{initial_greeting_text}</Say>")

    # Añadir una pausa para mantener la llamada viva
    twiml_parts.append("  <Pause length='60'/>") # Aumentado a 60s
    twiml_parts.append("</Response>")

    twiml = "".join(twiml_parts)




    print(f"CLEAN TwiML check: {twiml}") # Nuevo log de verificación
    return Response(content=twiml, media_type="text/xml")