# backend/app/stt.py (CORREGIDO)

import asyncio
import audioop
import os
import time
import json
import base64
from fastapi import WebSocket

# Importar las bibliotecas de Google Cloud
from google.cloud import speech_v1p1beta1 as speech
from google.oauth2 import service_account

from .supabase import save_transcript

# Twilio siempre envía audio a 8kHz μ-law mono
SAMPLE_RATE = 8000

# Configuración de Google Cloud
# Cargar las credenciales JSON desde una variable de entorno
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

# Inicializar cliente de Google Cloud Speech una vez
speech_client = None
try:
    if GOOGLE_APPLICATION_CREDENTIALS_JSON:
        credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        speech_client = speech.SpeechClient(credentials=credentials)
    else:
        speech_client = speech.SpeechClient()
    print("Google Speech Client initialized successfully.")
except Exception as e:
    print(f"Error initializing Google Speech Client: {e}")
    speech_client = None


def mulaw_to_linear16(data: bytes) -> bytes:
    """Convierte audio μ-law (8kHz, mono) a PCM LINEAR16 (8kHz, mono)."""
    return audioop.ulaw2lin(data, 2)


async def process_stream(ws: WebSocket) -> None:
    """
    Maneja el ciclo de vida completo del WebSocket de Twilio Media Stream:
    1. Espera los eventos 'connected' y 'start'.
    2. Extrae el call_id.
    3. Procesa los eventos 'media' enviando audio a Google STT.
    4. Guarda las transcripciones finales.
    5. Maneja el evento 'stop'.
    """
    if not speech_client:
        print("Google Speech Client not initialized. Cannot process STT stream.")
        return

    call_id = None
    stream_sid = None
    
    # --- Bucle de inicialización para obtener el call_id ---
    # Es crucial procesar los mensajes 'connected' y 'start' primero.
    while call_id is None:
        try:
            message = await ws.receive_text()
            data = json.loads(message)
            event = data.get("event")

            if event == "connected":
                print("Twilio stream is connected.")
            elif event == "start":
                stream_sid = data.get("streamSid")
                call_id = data.get("start", {}).get("callSid")
                print(f"[{call_id}] Stream started. (StreamSid: {stream_sid})")
                break # Salimos del bucle de inicialización
            else:
                print(f"Received unexpected event during startup: {event}")
        
        except Exception as e:
            print(f"Error during WebSocket startup phase: {e}")
            return # Si no podemos inicializar, cerramos.

    # Si no obtuvimos un call_id, no podemos continuar.
    if not call_id:
        print("Failed to get call_id from 'start' event. Closing stream.")
        return

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE,
        language_code="es-ES",
        model="phone_call",
        enable_automatic_punctuation=True,
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=False, # Ponlo en False si solo te importan los resultados finales
    )

    # El generador de peticiones ahora se alimenta de un 'async_queue'
    # para desacoplar la recepción de la transmisión.
    async_queue = asyncio.Queue()

    async def request_generator():
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        while True:
            chunk = await async_queue.get()
            if chunk is None:
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)
            
    # Función síncrona que procesa las respuestas de Google en un hilo
    def process_responses(responses, loop):
        ts_start = time.time()
        for response in responses:
            for result in response.results:
                if result.is_final:
                    text = result.alternatives[0].transcript.strip()
                    ts_end = time.time()
                    if text:
                        print(f"[{call_id}] Final Transcribed: {text}")
                        asyncio.run_coroutine_threadsafe(
                            save_transcript(call_id, ts_start, ts_end, text), 
                            loop
                        )
                    ts_start = ts_end

    # Tarea que escucha el WebSocket y pone los chunks de audio en la cola
    async def receive_audio_task():
        try:
            while True:
                message = await ws.receive_text()
                data = json.loads(message)
                event = data.get("event")

                if event == "media":
                    payload = data["media"]["payload"]
                    audio_chunk = base64.b64decode(payload)
                    linear16_chunk = mulaw_to_linear16(audio_chunk)
                    await async_queue.put(linear16_chunk)
                elif event == "stop":
                    print(f"[{call_id}] Received 'stop' event. Stopping stream.")
                    await async_queue.put(None) # Señal para terminar el generador
                    break
        except Exception as e:
            print(f"[{call_id}] Error in receive_audio_task: {e}")
            await async_queue.put(None)

    # --- Ejecución Principal ---
    try:
        print(f"[{call_id}] Starting Google STT stream processing.")
        
        # Inicia la tarea que escucha el WebSocket en segundo plano
        receive_task = asyncio.create_task(receive_audio_task())

        requests = request_generator()
        responses_iterator = speech_client.streaming_recognize(requests=requests)
        
        loop = asyncio.get_running_loop()
        
        # Ejecuta el procesamiento bloqueante en un hilo
        await loop.run_in_executor(
            None, 
            process_responses,
            responses_iterator,
            loop
        )

        # Espera a que la tarea de recepción termine
        await receive_task

    except Exception as e:
        print(f"[{call_id}] An error occurred during STT stream processing: {e}")
    finally:
        print(f"[{call_id}] STT stream processing finished.")