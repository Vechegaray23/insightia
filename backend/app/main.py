import os
from fastapi import FastAPI, Response, WebSocket
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
    inicia Twilio Media Streams para STT y espera la entrada del usuario.
    """
    initial_greeting_text = "Por favor, dígame lo que necesita."
    
    greeting_audio_url = None
    try:
        greeting_audio_url = await speak(initial_greeting_text)
    except Exception as e:
        print(f"Error generating TTS audio for greeting: {e}")
        
    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL", "wss://insightia-production.up.railway.app/stt")
    
    twiml_parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<Response>",
        "  <Start>",
        f"    <Stream url='{websocket_url}' />",
        "  </Start>"
    ]

    if greeting_audio_url:
        twiml_parts.append(f"  <Play>{greeting_audio_url}</Play>")
    else:
        twiml_parts.append(f"  <Say>{initial_greeting_text}</Say>")

    # --- NUEVA ADICIÓN: <Gather> para mantener la llamada activa y esperar la voz del usuario ---
    # input='speech': Twilio escuchará la voz.
    # speechTimeout='auto': Twilio detectará automáticamente cuándo el usuario deja de hablar.
    # timeout='10': Twilio esperará hasta 10 segundos de silencio antes de finalizar la espera (si no hay speech).
    # action: URL a la que Twilio enviará el resultado de la voz del usuario.
    #         Si no se especifica, Twilio volverá a enviar la solicitud a la URL actual (/voice).
    #         Para un flujo de conversación completo, necesitarías un endpoint dedicado para esto.
    twiml_parts.append(
        "  <Gather input='speech' speechTimeout='auto' timeout='10'>"
        "  </Gather>"
        "</Response>"
    )
    
    twiml = "".join(twiml_parts)
    print(f"Generated TwiML: {twiml}") # Para depuración
    return Response(content=twiml, media_type="text/xml")