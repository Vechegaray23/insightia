# backend/app/stt.py (VERSIÓN FINAL CORREGIDA)

import asyncio
import audioop
import os
import time
import json
import base64
import traceback
from fastapi import WebSocket

from google.cloud import speech_v1p1beta1 as speech
from google.oauth2 import service_account

from .supabase import save_transcript

SAMPLE_RATE = 8000

# --- Configuración de Google Cloud ---
speech_client = None
try:
    GOOGLE_APPLICATION_CREDENTIALS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if GOOGLE_APPLICATION_CREDENTIALS_JSON:
        credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        speech_client = speech.SpeechClient(credentials=credentials)
    else:
        speech_client = speech.SpeechClient()
    print("Google Speech Client inicializado correctamente.")
except Exception as e:
    print(f"Error CRÍTICO al inicializar Google Speech Client: {e}")

def mulaw_to_linear16(data: bytes) -> bytes:
    return audioop.ulaw2lin(data, 2)


async def process_stream(ws: WebSocket, call_id: str) -> None:
    if not speech_client:
        print(f"[{call_id}] Abortando: Google Speech Client no inicializado.")
        return

    print(f"[{call_id}] Iniciando el procesamiento del stream de STT.")
    async_queue = asyncio.Queue()

    async def request_generator():
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        while True:
            chunk = await async_queue.get()
            if chunk is None: break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    def process_responses(responses, loop):
        ts_start = time.time()
        for response in responses:
            for result in response.results:
                if result.is_final:
                    text = result.alternatives[0].transcript.strip()
                    if text:
                        print(f"[{call_id}] Transcripción final: '{text}'")
                        ts_end = time.time()
                        asyncio.run_coroutine_threadsafe(
                            save_transcript(call_id, ts_start, ts_end, text), loop
                        )
                        ts_start = ts_end

    async def receive_audio_task():
        while True:
            message = await ws.receive_text()
            data = json.loads(message)
            event = data.get("event")
            if event == "media":
                audio_chunk = base64.b64decode(data["media"]["payload"])
                await async_queue.put(mulaw_to_linear16(audio_chunk))
            elif event == "stop":
                print(f"[{call_id}] Evento 'stop' recibido. Finalizando recepción.")
                await async_queue.put(None)
                break

    try:
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code="es-ES",
            model="phone_call",
            enable_automatic_punctuation=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(config=config, interim_results=False)

        receive_task = asyncio.create_task(receive_audio_task())
        requests = request_generator()

        # --- LA CORRECCIÓN ESTÁ AQUÍ ---
        # Añadimos el argumento 'config=streaming_config' que faltaba.
        responses_iterator = speech_client.streaming_recognize(
            streaming_config=streaming_config,
            requests=request_generator()
        )
        # --- FIN DE LA CORRECCIÓN ---
        
        print(f"[{call_id}] Conexión con Google STT API establecida. Escuchando audio...")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process_responses, responses_iterator, loop)

        await receive_task

    except Exception as e:
        print(f"[{call_id}] ERROR CRÍTICO en process_stream: {e}\n{traceback.format_exc()}")
    finally:
        print(f"[{call_id}] Finalizando el stream STT.")