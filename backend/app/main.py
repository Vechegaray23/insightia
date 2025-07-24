# backend/app/main.py

import os
import json
import traceback
import logging
from fastapi import FastAPI, WebSocket
from fastapi import Response
from . import stt, wer, tts

logger = logging.getLogger(__name__)

app = FastAPI()


# --- WebSocket Endpoint ---
# Responsable de manejar la conexión de audio en tiempo real de Twilio.
@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    """
    Manejador del WebSocket. Acepta la conexión, extrae el CallSid del evento 'start'
    y delega el procesamiento del stream de audio a stt.py.
    """
    logger.info("MAIN.PY-STT: 1. Conexión WebSocket recibida. Aceptando...")
    await websocket.accept()
    call_id = None

    try:
        logger.debug(
            "MAIN.PY-STT: 2. Entrando en bucle de inicialización para obtener el CallSid."
        )
        # Bucle para encontrar el evento 'start', que es el que contiene el CallSid.
        # Es robusto ante la llegada de otros eventos como 'connected' primero.
        while True:
            message = await websocket.receive_json()
            logger.debug(
                "MAIN.PY-STT: 3. Mensaje de inicialización recibido: %s", message
            )
            data = message
            event = data.get("event")

            if event == "start":
                call_id = data.get("start", {}).get("callSid")
                logger.info(
                    "[%s] Evento 'start' procesado. CallSid obtenido exitosamente.",
                    call_id,
                )
                break  # Salir del bucle, ya tenemos lo que necesitamos.
            elif event == "connected":
                logger.debug(
                    "Evento 'connected' de Twilio recibido. Esperando 'start'..."
                )
            else:
                # Ignorar otros eventos (como 'media') que podrían llegar durante esta fase.
                pass

        if not call_id:
            logger.warning("No se recibió call_id en el evento 'start'. Usando 'test'.")
            call_id = "test"

        logger.info(
            "MAIN.PY-STT: 4. Delegando a stt.process_stream para la llamada: %s",
            call_id,
        )
        await stt.process_stream(websocket, call_id)
        logger.info(
            "MAIN.PY-STT: 5. stt.process_stream ha terminado su ejecución para la llamada: %s",
            call_id,
        )

    except Exception as e:
        # Captura y registra cualquier error inesperado para un diagnóstico completo.
        logger.exception(
            "MAIN.PY-STT: ERROR CRÍTICO en el manejador del WebSocket: %s", e
        )
    finally:
        # Este bloque se ejecutará siempre, confirmando el fin del ciclo de vida del handler.
        logger.info(
            "MAIN.PY-STT: 6. Bloque 'finally' alcanzado. [%s] El manejador del WebSocket ha finalizado.",
            call_id or "unknown",
        )


# --- TwiML Endpoint ---
# El primer punto de contacto para la llamada de Twilio.
@app.post("/voice")
async def voice():
    """
    Devuelve TwiML que:
    1. Inicia un stream de audio a nuestro WebSocket.
    2. Reproduce un saludo (generado por TTS o cacheado).
    3. Mantiene la llamada activa para que el stream pueda continuar.
    """
    logger.info("VOICE: Endpoint /voice activado (VERSIÓN FINAL Y LIMPIA).")
    initial_greeting_text = "¿Cómo puedo ayudarte hoy?"
    greeting_audio_url = None

    try:
        greeting_audio_url = await tts.speak(initial_greeting_text)
    except Exception as e:
        logger.exception("VOICE: Error generando audio TTS: %s", e)

    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL")
    if not websocket_url:
        logger.error(
            "VOICE ERROR: La variable de entorno TWILIO_WEBSOCKET_URL no está configurada."
        )
        websocket_url = "ws://localhost/stt"

    # Construcción pieza por pieza para garantizar un TwiML 100% válido.
    twiml_parts = ["<?xml version='1.0' encoding='UTF-8'?>", "<Response>"]
    twiml_parts.extend(
        ["  <Start>", f"    <Stream url='{websocket_url}' />", "  </Start>"]
    )
    if greeting_audio_url:
        twiml_parts.append(f"  <Play>{greeting_audio_url}</Play>")
    else:
        twiml_parts.append(f"  <Say>{initial_greeting_text}</Say>")

    twiml_parts.extend(
        [
            "  <Pause length='20'/>",  # Mantiene la llamada activa para que el stream continúe.
            "</Response>",
        ]
    )

    twiml = "".join(twiml_parts)
    logger.debug("VOICE: TwiML generado (verificación final):\n%s", twiml)
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
    wer.metrics.add(score)
    return {"wer": score}


@app.get("/metrics")
def metrics():
    """Endpoint para métricas (placeholder)."""
    return wer.metrics.metrics()
