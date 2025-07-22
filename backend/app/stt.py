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


async def process_stream(ws: WebSocket, call_id: str) -> None:
    """
    Procesa audio por WebSocket, lo envía a Google Cloud Speech-to-Text y emite transcripciones.
    """
    if not speech_client:
        print(f"[{call_id}] Google Speech Client not initialized. Cannot process STT stream.")
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
        interim_results=True,
    )

    # El generador de peticiones que se alimenta de los mensajes del WebSocket
    async def request_generator():
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        try:
            while True:
                # Espera por el siguiente mensaje del WebSocket
                message = await ws.receive_text()
                data = json.loads(message)
                
                if data.get("event") == "media":
                    payload = data["media"]["payload"]
                    audio_chunk = base64.b64decode(payload)
                    linear16_chunk = mulaw_to_linear16(audio_chunk)
                    yield speech.StreamingRecognizeRequest(audio_content=linear16_chunk)
                elif data.get("event") == "stop":
                    print(f"[{call_id}] Received 'stop' event from Twilio.")
                    break
        except Exception as e:
            print(f"[{call_id}] Error in request generator: {e}")

    # Función síncrona que procesará las respuestas de Google
    def process_responses(responses, loop):
        ts_start = time.time()
        for response in responses:
            for result in response.results:
                if result.is_final:
                    text = result.alternatives[0].transcript
                    ts_end = time.time()
                    if text and text.strip():
                        print(f"[{call_id}] Final Transcribed: {text}")
                        # Usamos call_soon_threadsafe para interactuar con el bucle de eventos desde el hilo
                        # y llamar a la corrutina save_transcript
                        asyncio.run_coroutine_threadsafe(
                            save_transcript(call_id, ts_start, ts_end, text), 
                            loop
                        )
                        # También podemos enviar la transcripción de vuelta por el WebSocket
                        asyncio.run_coroutine_threadsafe(
                            ws.send_text(json.dumps({"transcript": text})),
                            loop
                        )
                    ts_start = ts_end
    
    try:
        print(f"[{call_id}] Starting Google STT stream processing.")
        # Obtenemos el generador asíncrono
        requests = request_generator()
        # Llamamos a la API de Google
        responses_iterator = speech_client.streaming_recognize(requests=requests)
        
        # Obtenemos el bucle de eventos actual de asyncio
        loop = asyncio.get_running_loop()
        
        # Ejecutamos la función de procesamiento síncrona en un hilo separado
        await loop.run_in_executor(
            None,  # Usa el ejecutor de hilos por defecto
            process_responses,
            responses_iterator,
            loop
        )

    except Exception as e:
        # Este error ahora capturará problemas más serios, como de conexión.
        print(f"[{call_id}] An error occurred during STT stream processing: {e}")
    finally:
        print(f"[{call_id}] STT stream processing finished.")