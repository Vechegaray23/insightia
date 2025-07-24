# backend/app/stt.py (VERSIÓN FINAL CORREGIDA)

import asyncio
import audioop
import os
import time
import json
import base64
import traceback
import logging
from fastapi import WebSocket

try:
    from google.cloud import speech_v1p1beta1 as speech
    from google.oauth2 import service_account
except Exception:  # pragma: no cover - optional dependency
    speech = None
    service_account = None

from .supabase import save_transcript

logger = logging.getLogger(__name__)

SAMPLE_RATE = 8000
CHUNK_SIZE = 320

# --- Configuración de Google Cloud ---
speech_client = None
recognition_config = None
streaming_config = None
if speech and service_account:
    try:
        GOOGLE_APPLICATION_CREDENTIALS_JSON = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS_JSON"
        )
        if GOOGLE_APPLICATION_CREDENTIALS_JSON:
            credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info
            )
            speech_client = speech.SpeechClient(credentials=credentials)
        else:
            speech_client = speech.SpeechClient()
        logger.info("Google Speech Client inicializado correctamente.")
        recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code="es-ES",
            model="phone_call",
            enable_automatic_punctuation=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=False,
        )
    except Exception as e:
        logger.exception("Error CRÍTICO al inicializar Google Speech Client: %s", e)
else:
    logger.warning("google.cloud.speech library not available. STT disabled.")


def mulaw_to_linear16(data: bytes) -> bytes:
    return audioop.ulaw2lin(data, 2)


def transcribe_chunk(wav: bytes) -> str:
    """Placeholder synchronous transcription for tests."""
    return ""


async def process_stream(ws: WebSocket, call_id: str) -> None:
    if not speech_client:
        logger.warning(
            "[%s] Google Speech Client no disponible. Usando transcribe_chunk.",
            call_id,
        )
        while True:
            data = await ws.receive_json()
            event = data.get("event")
            if event == "media":
                audio_chunk = base64.b64decode(data["media"]["payload"])
                text = transcribe_chunk(mulaw_to_linear16(audio_chunk))
                if text:
                    await ws.send_text(text)
            elif event == "stop":
                logger.info(
                    "[%s] Evento 'stop' recibido. Finalizando recepción.", call_id
                )
                break
        return

    logger.info("[%s] Iniciando el procesamiento del stream de STT.", call_id)
    loop = asyncio.get_running_loop()
    async_queue = asyncio.Queue()

    def generate_requests():
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        while True:
            chunk = asyncio.run_coroutine_threadsafe(async_queue.get(), loop).result()
            if chunk is None:
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    def process_responses(responses, loop):
        ts_start = time.time()
        for response in responses:
            for result in response.results:
                if result.is_final:
                    text = result.alternatives[0].transcript.strip()
                    if text:
                        logger.info("[%s] Transcripción final: '%s'", call_id, text)
                        ts_end = time.time()
                        asyncio.run_coroutine_threadsafe(
                            save_transcript(call_id, ts_start, ts_end, text), loop
                        )
                        ts_start = ts_end

    async def receive_audio_task():
        while True:
            data = await ws.receive_json()
            event = data.get("event")
            if event == "media":
                audio_chunk = base64.b64decode(data["media"]["payload"])
                await async_queue.put(mulaw_to_linear16(audio_chunk))
            elif event == "stop":
                logger.info(
                    "[%s] Evento 'stop' recibido. Finalizando recepción.", call_id
                )
                await async_queue.put(None)
                break

    try:
        receive_task = asyncio.create_task(receive_audio_task())

        responses_iterator = speech_client.streaming_recognize(
            requests=generate_requests()
        )

        logger.info(
            "[%s] Conexión con Google STT API establecida. Escuchando audio...",
            call_id,
        )

        await loop.run_in_executor(None, process_responses, responses_iterator, loop)

        await receive_task

    except Exception as e:
        logger.exception("[%s] ERROR CRÍTICO en process_stream: %s", call_id, e)
    finally:
        logger.info("[%s] Finalizando el stream STT.", call_id)
