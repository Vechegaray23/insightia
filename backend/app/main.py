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
    """
    Punto de entrada para la conexión WebSocket de Twilio con logging detallado.
    """
    # Log #1: ¿Se está llamando a la función?
    print("Endpoint /stt alcanzado. Intentando aceptar la conexión...")
    await websocket.accept()
    # Log #2: ¿La conexión fue aceptada?
    print("WebSocket connection accepted. Delegating to process_stream...")
    
    try:
        await stt.process_stream(websocket)
    except Exception:
        # Log #3: Si CUALQUIER error ocurre, lo veremos aquí.
        print("!!! An unexpected error occurred in the WebSocket handler !!!")
        print(traceback.format_exc()) # Imprime la traza completa del error
    finally:
        # Log #4: ¿Cuándo se está cerrando la conexión?
        print("WebSocket handler finished. Connection will now close.")

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
        "<Response>"
    ]

    if greeting_audio_url:
        twiml_parts.append(f"<Play>{greeting_audio_url}</Play>") # Eliminados espacios para simplificar
    else:
        twiml_parts.append(f"<Say>{initial_greeting_text}</Say>")

    twiml_parts.append("<Connect>")
    twiml_parts.append(f"<Stream url='{websocket_url}'/>") # Eliminados espacios para simplificar
    twiml_parts.append("</Connect>")
    twiml_parts.append("</Response>")

    twiml = "".join(twiml_parts)
    print(f"CLEAN TwiML check: {twiml}") # Nuevo log de verificación
    return Response(content=twiml, media_type="text/xml")