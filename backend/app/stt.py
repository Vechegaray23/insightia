import audioop
import io
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
        # Esto es útil para desarrollo local si ya has configurado gcloud auth application-default login
        # O si el entorno de ejecución (como GCP) proporciona credenciales por defecto.
        speech_client = speech.SpeechClient()
    print("Google Speech Client initialized successfully.")
except Exception as e:
    print(f"Error initializing Google Speech Client: {e}")
    speech_client = None


def mulaw_to_linear16(data: bytes) -> bytes:
    """Convierte audio μ-law (8kHz, mono) a PCM LINEAR16 (8kHz, mono)."""
    # audioop.ulaw2lin convierte 8-bit mu-law a 16-bit linear PCM.
    # El 2 indica que el output PCM tendrá un ancho de muestra de 2 bytes (16 bits).
    return audioop.ulaw2lin(data, 2)


async def process_stream(ws: WebSocket, call_id: str) -> None:
    """
    Procesa audio por WebSocket, lo envía a Google Cloud Speech-to-Text y emite transcripciones.
    Maneja diferentes tipos de mensajes de Twilio Media Streams.
    """
    if not speech_client:
        print(f"[{call_id}] Google Speech Client not initialized. Cannot process STT stream.")
        return

    buffer = b""
    # Definimos un tamaño de chunk para enviar a Google STT.
    # Google puede manejar tamaños pequeños, 250ms de audio es un buen compromiso.
    # 8000 muestras/seg * 2 bytes/muestra (LINEAR16) * 0.25 segundos = 4000 bytes
    GOOGLE_STT_CHUNK_BYTES = SAMPLE_RATE * 2 * 0.25

    print(f"[{call_id}] Starting Google STT stream processing.")

    # Configuración de la solicitud de streaming para Google Cloud Speech
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE, # 8000 Hz por Twilio
        language_code="es-ES", # Asegúrate de que coincida con el idioma esperado
        model="phone_call", # Optimizado para audio de llamadas telefónicas
        enable_automatic_punctuation=True, # Mejora la legibilidad de la transcripción
        # use_enhanced=True, # Puedes probar con el modelo "enhanced" si está disponible para "phone_call"
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True, # Para obtener resultados parciales mientras el usuario habla
    )

    # El generador de audio se encargará de decodificar y enviar los fragmentos LINEAR16
    audio_generator = _generate_audio_requests(ws, call_id, GOOGLE_STT_CHUNK_BYTES)
    # Crea un iterador de StreamingRecognizeRequest a partir del generador de audio
    requests = (speech.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)

    stream_active = True
    try:
        # Inicia el stream de reconocimiento con Google Cloud Speech
        responses = speech_client.streaming_recognize(streaming_config, requests)

        ts_start = time.time() # Timestamp para el inicio del segmento de habla actual

        # Procesa las respuestas del stream de Google STT
        for response in responses:
            # Google Cloud STT envía resultados en el campo 'results'
            for result in response.results:
                if result.is_final:
                    text = result.alternatives[0].transcript
                    ts_end = time.time()
                    if text and text.strip():
                        await save_transcript(call_id, ts_start, ts_end, text)
                        print(f"[{call_id}] Final Transcribed: {text}")
                        await ws.send_text(text)
                    ts_start = ts_end # Reiniciar el timestamp para el siguiente segmento final
                # else:
                #     # Resultados interinos (opcional, puedes enviarlos al frontend para feedback en tiempo real)
                #     interim_text = result.alternatives[0].transcript
                #     print(f"[{call_id}] Interim: {interim_text}")
                #     await ws.send_text(f"[Interim]: {interim_text}") # Puedes enviar esto al frontend si lo necesitas

    except Exception as e:
        print(f"[{call_id}] Error processing Google STT stream: {e}")
    finally:
        print(f"[{call_id}] STT stream processing finished. Final buffer size: {len(buffer)}")


async def _generate_audio_requests(ws: WebSocket, call_id: str, chunk_size_bytes: int):
    """Generador que produce fragmentos de audio LINEAR16 para la API de Google STT."""
    buffer = b""
    stream_active = True
    try:
        while stream_active:
            # Espera por cualquier tipo de mensaje de Twilio
            message = await ws.receive()

            if "text" in message:
                try:
                    control_data = json.loads(message["text"])
                    event = control_data.get("event")

                    if event == "media":
                        payload_b64 = control_data.get("media", {}).get("payload", "")
                        if payload_b64:
                            # Decodificar Twilio μ-law y convertir a LINEAR16
                            raw_mulaw = base64.b64decode(payload_b64)
                            buffer += mulaw_to_linear16(raw_mulaw)

                            # Enviar fragmentos a Google STT una vez que tenemos suficientes bytes
                            while len(buffer) >= chunk_size_bytes:
                                chunk = buffer[:chunk_size_bytes]
                                buffer = buffer[chunk_size_bytes:]
                                yield chunk # Envía el fragmento de audio al stream de Google
                    elif event == "stop":
                        print(f"[{call_id}] Twilio Media Stream 'stop' event received.")
                        if buffer: # Enviar cualquier audio restante antes de finalizar
                            yield buffer
                        stream_active = False # Salir del bucle
                    # else:
                    #     print(f"[{call_id}] Received control message: {event}")

                except json.JSONDecodeError:
                    print(f"[{call_id}] Received non-JSON text message: {message['text']}")
            elif message is None: # La conexión WebSocket se cerró inesperadamente por el cliente
                print(f"[{call_id}] WebSocket connection closed by client unexpectedly.")
                stream_active = False # Salir del bucle
    except Exception as e:
        print(f"[{call_id}] Error in audio generator: {e}")
    finally:
        print(f"[{call_id}] Audio generator finished.")