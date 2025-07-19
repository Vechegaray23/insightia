import os
from fastapi import FastAPI, Response, WebSocket # Asegúrate de importar WebSocket
import json # Necesario para parsear el mensaje inicial del WebSocket

from .tts import speak
from . import stt, wer

app = FastAPI()

@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    """
    Recibe audio μ-law de Twilio Media Streams y delega el procesamiento.
    Intenta extraer el call_id de los metadatos iniciales de Twilio.
    """
    await websocket.accept() # Aceptar la conexión WebSocket

    call_id = "unknown-call" # Valor por defecto

    try:
        # El primer mensaje de Twilio Media Streams suele ser un JSON con el evento "start"
        initial_message = await websocket.receive_json()
        if initial_message.get("event") == "start":
            call_sid = initial_message.get("start", {}).get("callSid")
            if call_sid:
                call_id = call_sid
                print(f"[{call_id}] Received callSid: {call_id}") # Para depuración
    except Exception as e:
        print(f"Error receiving initial WebSocket message or call_id: {e}")
        # Continuar con el call_id por defecto si falla la obtención

    # stt.process_stream ahora debe ser una función asíncrona
    await stt.process_stream(websocket, call_id)
    print(f"[{call_id}] WebSocket connection closed.")


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
    Devuelve TwiML que reproduce un saludo TTS de OpenAI y luego
    inicia Twilio Media Streams para STT.
    """
    initial_greeting_text = "Por favor, dígame lo que necesita."
    
    # Intenta generar la URL del audio del saludo usando tts.speak (voz OpenAI)
    greeting_audio_url = None
    try:
        greeting_audio_url = await speak(initial_greeting_text) # Asíncrono
    except Exception as e:
        print(f"Error generating TTS audio for greeting: {e}")
        # Si falla, se usará <Say> con la voz por defecto de Twilio
        
    # La URL pública de tu aplicación, apuntando al endpoint WebSocket /stt
    # DEBES configurar TWILIO_WEBSOCKET_URL en tus variables de entorno en Railway.
    # Por ejemplo: TWILIO_WEBSOCKET_URL=wss://insightia-production.up.railway.app/stt
    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL", "wss://insightia-production.up.railway.app/stt")
    
    twiml_parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<Response>",
        "  <Start>",
        f"    <Stream url='{websocket_url}' />",
        "  </Start>"
    ]

    if greeting_audio_url:
        # Si se generó el audio TTS de OpenAI, lo reproducimos con <Play>
        twiml_parts.append(f"  <Play>{greeting_audio_url}</Play>")
    else:
        # Si la generación de TTS falló, usamos <Say> con la voz por defecto de Twilio
        twiml_parts.append(f"  <Say>{initial_greeting_text}</Say>")

    twiml_parts.append("</Response>")
    
    twiml = "".join(twiml_parts)
    print(f"Generated TwiML: {twiml}") # Para depuración
    return Response(content=twiml, media_type="text/xml")