# backend/app/main.py
import os
from fastapi import FastAPI, Response, WebSocket
import json # Necesario para parsear el mensaje inicial del WebSocket

from .tts import speak
from . import stt, wer


app = FastAPI()
@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    """
    Punto de entrada para la conexión WebSocket de Twilio.
    Acepta la conexión y delega todo el procesamiento al módulo STT.
    """
    await websocket.accept()
    print("WebSocket connection accepted from Twilio.")
    
    try:
        # Pasa el control total al procesador de stream
        await stt.process_stream(websocket)
    except Exception as e:
        # Captura cualquier error inesperado que pueda cerrar la conexión
        print(f"Error in WebSocket handler: {e}")
    finally:
        print("WebSocket connection closed.")

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
    initial_greeting_text = "Nuestra misión es compartir la belleza de las palabras y las historias que se tejen con ellas. ¿Cómo puedo ayudarte hoy?"
    
    greeting_audio_url = None
    try:
        # Generamos el audio del saludo por adelantado para una respuesta rápida
        greeting_audio_url = await speak(initial_greeting_text)
    except Exception as e:
        print(f"Error generating TTS audio for greeting: {e}")
        
    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL", "wss://insightia-production.up.railway.app/stt")
    
    twiml_parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<Response>"
    ]

    # Reproducir el saludo inicial
    if greeting_audio_url:
        twiml_parts.append(f"  <Play>{greeting_audio_url}</Play>")
    else:
        # Fallback a Say si el TTS falla
        twiml_parts.append(f"  <Say>{initial_greeting_text}</Say>")

    # Iniciar la conexión persistente del WebSocket para la conversación
    twiml_parts.append("  <Connect>")
    twiml_parts.append(f"    <Stream url='{websocket_url}' />")
    twiml_parts.append("  </Connect>")
    twiml_parts.append("</Response>")
    
    twiml = "".join(twiml_parts)
    print(f"Generated TwiML for conversational flow: {twiml}")
    return Response(content=twiml, media_type="text/xml")