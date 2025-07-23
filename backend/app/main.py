# backend/app/main.py

import os
import json
import traceback
from fastapi import FastAPI, Response, WebSocket
from . import stt, wer, tts

app = FastAPI()

# --- WebSocket Endpoint ---
@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    print("MAIN.PY-STT: 1. WebSocket ACEPTADO")
    await websocket.accept()
    call_id = None

    try:
        print("MAIN.PY-STT: 2. Entrando en bucle de inicialización para obtener CallSid.")
        # Bucle para encontrar el evento 'start', que contiene el CallSid.
        while True:
            message = await websocket.receive_text()
            print(f"MAIN.PY-STT: 3. Mensaje de inicialización recibido: {message[:250]}")
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                call_id = data.get("start", {}).get("callSid")
                print(f"[{call_id}] Evento 'start' procesado. CallSid obtenido.")
                break  # Salir del bucle una vez que tenemos el call_id
            elif event == "connected":
                print("Evento 'connected' de Twilio recibido.")
            else:
                # Ignorar otros eventos como 'media' que podrían llegar durante la inicialización
                pass

        if not call_id:
            raise RuntimeError("No se pudo extraer el call_id del evento 'start'.")

        print(f"MAIN.PY-STT: 4. Llamando a stt.process_stream para call_id: {call_id}")
        await stt.process_stream(websocket, call_id)
        print(f"MAIN.PY-STT: 5. stt.process_stream ha terminado su ejecución.")

    except Exception as e:
        print(f"MAIN.PY-STT: ERROR CRÍTICO en el manejador del WebSocket: {e}")
        print(traceback.format_exc())
    finally:
        # Este bloque se ejecutará siempre, indicando que la función está terminando.
        print(f"MAIN.PY-STT: 6. Bloque 'finally' alcanzado. [{call_id or 'unknown'}] El manejador del WebSocket ha finalizado.")

# --- TwiML Endpoint ---
@app.post("/voice")
async def voice():
    """Devuelve TwiML para iniciar el stream y la llamada."""
    print("VOICE: Endpoint /voice activado.")
    initial_greeting_text = "Nuestra misión es compartir la belleza de las palabras y las historias que se tejen con ellas. ¿Cómo puedo ayudarte hoy?"
    greeting_audio_url = None
    try:
        greeting_audio_url = await tts.speak(initial_greeting_text)
    except Exception as e:
        print(f"VOICE: Error generando audio TTS: {e}")

    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL")
    if not websocket_url:
        return Response(content="Error: TWILIO_WEBSOCKET_URL no está configurada.", status_code=500)

    # Usar <Start> para un stream no bloqueante y <Pause> para mantener la llamada activa.
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

    twiml_parts.extend(["  <Pause length='60'/>", "</Response>"])

    twiml = "".join(twiml_parts)
    print(f"VOICE: TwiML generado:\n{twiml}")
    return Response(content=twiml, media_type="text/xml")

# --- Endpoints de Soporte ---
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/wer")
def calc_wer(payload: dict) -> dict:
    ref = payload.get("reference", "")
    hyp = payload.get("hypothesis", "")
    score = wer.wer(ref, hyp)
    return {"wer": score}

@app.get("/metrics")
def metrics():
    return {}