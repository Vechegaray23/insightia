# backend/app/stt.py (VERSIÓN FINAL)

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

# Twilio envía audio a 8kHz μ-law mono, que convertiremos a LINEAR16 para Google.
SAMPLE_RATE = 8000

# --- Configuración de Google Cloud ---
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

speech_client = None
try:
    if GOOGLE_APPLICATION_CREDENTIALS_JSON:
        credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        speech_client = speech.SpeechClient(credentials=credentials)
    else:
        # Esto intentará usar las credenciales de entorno por defecto si la variable JSON no está.
        speech_client = speech.SpeechClient()
    print("Google Speech Client initialized successfully.")
except Exception as e:
    print(f"Error initializing Google Speech Client: {e}")
    speech_client = None


def mulaw_to_linear16(data: bytes) -> bytes:
    """Convierte audio μ-law (8kHz, mono) a PCM LINEAR16 (8kHz, mono)."""
    return audioop.ulaw2lin(data, 2)


async def process_stream(ws: WebSocket, call_id: str) -> None:
    """
    Procesa el stream de audio de Twilio, lo envía a Google STT y guarda las transcripciones.
    Asume que la conexión ya está establecida y el call_id ha sido extraído por el llamador.
    """
    if not speech_client:
        print(f"[{call_id}] Google Speech Client no está inicializado. No se puede procesar el stream.")
        return

    print(f"[{call_id}] Iniciando el procesamiento del stream de STT.")

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE,
        language_code="es-ES",
        model="phone_call",
        enable_automatic_punctuation=True,
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=False, # Solo nos interesan los resultados finales.
    )

    # Cola asíncrona para desacoplar la recepción de audio del envío a Google.
    async_queue = asyncio.Queue()

    async def request_generator():
        """Generador que alimenta la API de Google con chunks de audio desde la cola."""
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        while True:
            chunk = await async_queue.get()
            if chunk is None:
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    def process_responses(responses, loop):
        """Función síncrona que se ejecuta en un hilo para procesar las respuestas de Google."""
        ts_start = time.time()
        for response in responses:
            for result in response.results:
                if result.is_final:
                    text = result.alternatives[0].transcript.strip()
                    ts_end = time.time()
                    if text:
                        print(f"[{call_id}] Transcripción final recibida: '{text}'")
                        # Usamos run_coroutine_threadsafe para llamar a una corrutina desde un hilo síncrono.
                        asyncio.run_coroutine_threadsafe(
                            save_transcript(call_id, ts_start, ts_end, text),
                            loop
                        )
                    ts_start = ts_end

    async def receive_audio_task():
        """Tarea asíncrona que escucha el WebSocket y pone los chunks de audio en la cola."""
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
                    print(f"[{call_id}] Evento 'stop' recibido de Twilio. Finalizando el stream de audio.")
                    await async_queue.put(None)  # Señal para terminar el generador de peticiones.
                    break
        except Exception as e:
            print(f"[{call_id}] Error en la tarea de recepción de audio (receive_audio_task): {e}")
            await async_queue.put(None) # Asegurarse de que el otro hilo termine.

    # --- Ejecución Principal ---
    try:
        # Inicia la tarea que escucha el WebSocket en segundo plano.
        receive_task = asyncio.create_task(receive_audio_task())

        # Crea el generador de peticiones para Google.
        requests = request_generator()

        # Inicia la llamada a la API de Google, que devuelve un iterador de respuestas.
        responses_iterator = speech_client.streaming_recognize(requests=requests)

        loop = asyncio.get_running_loop()

        # Ejecuta el procesamiento de respuestas (que es bloqueante) en un hilo del executor.
        await loop.run_in_executor(
            None,
            process_responses,
            responses_iterator,
            loop
        )

        # Espera a que la tarea de recepción termine (lo hará cuando reciba 'stop' o un error).
        await receive_task

    except Exception as e:
        print(f"[{call_id}] Error inesperado durante el procesamiento del stream STT: {e}")
    finally:
        print(f"[{call_id}] Finalizado el procesamiento del stream STT.")
