# backend/app/main.py

import os
import json
import traceback
from fastapi import FastAPI, Response, WebSocket
from . import stt, wer, tts

app = FastAPI()

# --- WebSocket Endpoint ---
# Responsable de manejar la conexión de audio en tiempo real de Twilio.
@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    """
    Manejador del WebSocket. Acepta la conexión, extrae el CallSid del evento 'start'
    y delega el procesamiento del stream de audio a stt.py.
    """
    print("MAIN.PY-STT: 1. Conexión WebSocket recibida. Aceptando...")
    await websocket.accept()
    call_id = None

    try:
        print("MAIN.PY-STT: 2. Entrando en bucle de inicialización para obtener el CallSid.")
        # Bucle para encontrar el evento 'start', que es el que contiene el CallSid.
        # Es robusto ante la llegada de otros eventos como 'connected' primero.
        while True:
            message = await websocket.receive_text()
            print(f"MAIN.PY-STT: 3. Mensaje de inicialización recibido: {message[:250]}")
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                call_id = data.get("start", {}).get("callSid")
                print(f"[{call_id}] Evento 'start' procesado. CallSid obtenido exitosamente.")
                break  # Salir del bucle, ya tenemos lo que necesitamos.
            elif event == "connected":
                print(f"Evento 'connected' de Twilio recibido. Esperando 'start'...")
            else:
                # Ignorar otros eventos (como 'media') que podrían llegar durante esta fase.
                pass

        if not call_id:
            # Si salimos del bucle sin un call_id, algo fue muy mal.
            raise RuntimeError("No se pudo extraer el call_id del evento 'start' de Twilio.")

        print(f"MAIN.PY-STT: 4. Delegando a stt.process_stream para la llamada: {call_id}")
        await stt.process_stream(websocket, call_id)
        print(f"MAIN.PY-STT: 5. stt.process_stream ha terminado su ejecución para la llamada: {call_id}")

    except Exception as e:
        # Captura y registra cualquier error inesperado para un diagnóstico completo.
        print(f"MAIN.PY-STT: ERROR CRÍTICO en el manejador del WebSocket: {e}")
        print(traceback.format_exc())
    finally:
        # Este bloque se ejecutará siempre, confirmando el fin del ciclo de vida del handler.
        print(f"MAIN.PY-STT: 6. Bloque 'finally' alcanzado. [{call_id or 'unknown'}] El manejador del WebSocket ha finalizado.")


# --- TwiML Endpoint ---
# El primer punto de contacto para la llamada de Twilio.
@app.post("/voice")
async def voice():
    """
    Devuelve TwiML que:
    1. Inicia un stream de audio a nuestro WebSocket.
    2. Reproduce un saludo.
    3. Mantiene la llamada activa para que el stream pueda continuar.
    """
    print("VOICE: Endpoint /voice activado (VERSIÓN FINAL Y LIMPIA).")
    initial_greeting_text = "Nuestra misión es compartir la belleza de las palabras y las historias que se tejen con ellas. ¿Cómo puedo ayudarte hoy?"
    greeting_audio_url = None

    try:
        greeting_audio_url = await tts.speak(initial_greeting_text)
    except Exception as e:
        print(f"VOICE: Error generando audio TTS: {e}")

    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL")
    if not websocket_url:
        print("VOICE ERROR: La variable de entorno TWILIO_WEBSOCKET_URL no está configurada.")
        return Response(content="Error: Configuración del servidor incompleta.", status_code=500)

    # Construcción pieza por pieza para garantizar un TwiML 100% válido.
    twiml_parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<Response>"
    ]
    twiml_parts.extend([
        "  <Start>",
        f"    <Stream url='{websocket_url}' />",
        "  </Start>"
    ])
    if greeting_audio_url:
        twiml_parts.append(f"  <Play>{greeting_audio_url}</Play>")  # SIN CARACTERES ADICIONALES
    else:
        twiml_parts.append(f"  <Say>{initial_greeting_text}</Say>")

    twiml_parts.extend([
        "  <Pause length='60'/>", # Mantiene la llamada activa para que el stream continúe.
        "</Response>"
    ])

    twiml = "".join(twiml_parts)
    print(f"VOICE: TwiML generado (verificación final):\n{twiml}")
    return Response(content=twiml, media_type="text/xml")


# --- Endpoints de Soporte ---
@app.get("/health")
async def health() -> dict[str, str]:
    """Endpoint de health check para la plataforma de despliegue."""
    return {"status": "ok"}

@app.post("/wer")
def calc_wer(payload: dict) -> dict:
    """Calcula el Word Error Rate entre dos textos."""
    ref = payload.get("reference", "")
    hyp = payload.get("hypothesis", "")
    score = wer.wer(ref, hyp)
    return {"wer": score}

@app.get("/metrics")
def metrics():
    """Endpoint para métricas (placeholder)."""
    return {}