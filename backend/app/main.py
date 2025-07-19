import os
from fastapi import FastAPI, Response
from fastapi import WebSocket # Asegúrate de importar WebSocket
from .tts import speak
from . import stt, wer

app = FastAPI()

# Modificación: hacer el WebSocket asíncrono y capturar call_id
@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    """Recibir audio μ-law y devolver texto."""
    await websocket.accept() # Aceptar la conexión WebSocket

    call_id = "unknown-call"
    
    # Intenta obtener el call_id de los metadatos de Twilio Media Streams
    try:
        initial_message = await websocket.receive_json()
        if initial_message.get("event") == "start":
            call_sid = initial_message.get("start", {}).get("callSid")
            if call_sid:
                call_id = call_sid
                print(f"Received callSid: {call_id}") # Para depuración
    except Exception as e:
        print(f"Error receiving initial WebSocket message or call_id: {e}")
        # Continuar con el call_id por defecto si falla la obtención

    # Pasar el objeto websocket y el call_id al procesador de stream
    # Importante: stt.process_stream DEBE ser async ahora
    await stt.process_stream(websocket, call_id) 
    print(f"WebSocket connection for call {call_id} closed.")


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


# Modificación: El endpoint /voice ahora inicia Media Streams
@app.post("/voice")
async def voice():
    """Return TwiML that initiates Twilio Media Streams."""
    # La URL pública de tu aplicación, apuntando al endpoint WebSocket /stt
    # Aquí es donde usas la URL pública de tu deployment.
    # Usaremos una variable de entorno, si no está, usa un placeholder para recordar que debes configurarla.
    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL", "wss://insightia-production.up.railway.app/stt")
    
    twiml = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<Response>"
        "  <Start>"
        f"    <Stream url='{websocket_url}' />"
        "  </Start>"
        "  <Say>Por favor, dígame lo que necesita.</Say>" # Un saludo inicial opcional
        "</Response>"
    )
    return Response(content=twiml, media_type="text/xml")