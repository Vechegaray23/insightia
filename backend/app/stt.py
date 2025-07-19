"""Utilidades de STT con Whisper."""

import audioop
import io
import os
import time
import wave
import httpx
import json
from fastapi import WebSocket # Necesario para tipado y métodos asíncronos

from .supabase import save_transcript

SAMPLE_RATE = 16000
CHUNK_SECONDS = 5
CHUNK_SIZE = SAMPLE_RATE * CHUNK_SECONDS  # bytes for mu-law (1 byte per sample)


def mulaw_to_wav(data: bytes) -> bytes:
    """Convierte audio μ-law en un archivo WAV."""
    pcm = audioop.ulaw2lin(data, 2)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    return buffer.getvalue()


def transcribe_chunk(wav: bytes) -> str:
    """Envía audio a Whisper y devuelve el texto."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": ("audio.wav", wav, "audio/wav")}
    data = {"model": "whisper-1"}
    
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/audio/transcriptions", headers=headers, data=data, files=files, timeout=5 # Añadir timeout
        )
        resp.raise_for_status() # Lanza un HTTPStatusError para códigos de error 4xx/5xx
        return resp.json().get("text", "")
    except httpx.RequestError as e:
        print(f"An error occurred while requesting Whisper API: {e}")
        return "" # Devuelve cadena vacía en caso de error de red/conexión
    except httpx.HTTPStatusError as e:
        print(f"Whisper API returned an error {e.response.status_code}: {e.response.text}")
        return "" # Devuelve cadena vacía en caso de error de API


async def process_stream(ws: WebSocket, call_id: str) -> None:
    """
    Procesa audio por WebSocket, lo envía a Whisper y emite transcripciones.
    Maneja diferentes tipos de mensajes de Twilio Media Streams.
    """
    buffer = b""
    ts_start = time.time()
    
    print(f"[{call_id}] Starting STT stream processing.")

    stream_active = True # Controla el bucle principal
    try:
        while stream_active: 
            message = await ws.receive() # Espera por cualquier tipo de mensaje
            
            if "bytes" in message: # Si el mensaje es de tipo bytes (audio)
                chunk = message["bytes"]
                if not chunk:
                    # Si se recibe un chunk vacío, podría indicar una pausa o el fin del stream.
                    # No salimos inmediatamente, esperamos un evento 'stop' explícito.
                    print(f"[{call_id}] Empty audio chunk received. Keeping stream active.")
                    continue 
                
                buffer += chunk
                
                # Procesar chunks completos cuando el búfer alcanza el tamaño definido
                while len(buffer) >= CHUNK_SIZE:
                    raw = buffer[:CHUNK_SIZE]
                    buffer = buffer[CHUNK_SIZE:] # Quita el chunk procesado del buffer
                    
                    wav = mulaw_to_wav(raw)
                    text = transcribe_chunk(wav) # Llama a Whisper
                    ts_end = time.time()
                    
                    if text and text.strip(): # Solo guardar y enviar si hay texto significativo
                        await save_transcript(call_id, ts_start, ts_end, text)
                        print(f"[{call_id}] Transcribed: {text}") # Para depuración
                        await ws.send_text(text) # Enviar transcripción de vuelta al cliente (Twilio)
                    
                    ts_start = ts_end # Actualizar el inicio del siguiente chunk
            
            elif "text" in message:
                # Twilio puede enviar mensajes de control en texto (JSON) durante la llamada
                try:
                    control_data = json.loads(message["text"])
                    event = control_data.get("event")

                    if event == "stop":
                        print(f"[{call_id}] Twilio Media Stream 'stop' event received.")
                        
                        # --- MODIFICACIÓN CLAVE: Procesar el búfer restante ANTES de detenerse ---
                        if buffer:
                            print(f"[{call_id}] Processing remaining buffer ({len(buffer)} bytes) before stopping.")
                            wav = mulaw_to_wav(buffer)
                            text = transcribe_chunk(wav)
                            ts_end = time.time()
                            if text and text.strip():
                                await save_transcript(call_id, ts_start, ts_end, text)
                                print(f"[{call_id}] Transcribed (final chunk): {text}")
                                # No es estrictamente necesario enviar el último chunk a Twilio si la llamada se va a colgar.
                                # await ws.send_text(text) 
                        
                        stream_active = False # Cambiar la bandera para salir del bucle en la próxima iteración
                    elif event != "media": # Filtrar los ruidosos mensajes "media" que no son audio real
                        print(f"[{call_id}] Received control message: {event}")

                except json.JSONDecodeError:
                    print(f"[{call_id}] Received non-JSON text message: {message['text']}")
            
            elif message is None: # La conexión WebSocket se cerró inesperadamente por el cliente
                print(f"[{call_id}] WebSocket connection closed by client unexpectedly.")
                stream_active = False # Salir del bucle
                
    except Exception as e:
        print(f"[{call_id}] Error processing stream: {e}")
    finally:
        print(f"[{call_id}] STT stream processing finished. Final buffer size: {len(buffer)}")
        # El búfer ya fue procesado si se recibió un evento 'stop'.