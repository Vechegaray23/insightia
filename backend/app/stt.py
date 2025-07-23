# backend/app/stt.py
import audioop
import io
import os
import time
import wave
import httpx
import json
import base64
from fastapi import WebSocket # Necesario para tipado y métodos asíncronos

from .supabase import save_transcript

# Frecuencia del audio entrante de Twilio (μ-law)
INPUT_SAMPLE_RATE = int(os.getenv("TWILIO_SAMPLE_RATE", "8000"))
# Whisper requiere audio PCM a 16 kHz
WHISPER_SAMPLE_RATE = 16000
CHUNK_SECONDS = 5
CHUNK_SIZE = INPUT_SAMPLE_RATE * CHUNK_SECONDS  # bytes for μ-law (1 byte por muestra)


def mulaw_to_wav(data: bytes) -> bytes:
    """Convierte audio μ-law en un archivo WAV."""
    pcm = audioop.ulaw2lin(data, 2)
    sample_rate = INPUT_SAMPLE_RATE

    if INPUT_SAMPLE_RATE != WHISPER_SAMPLE_RATE:
        pcm, _ = audioop.ratecv(
            pcm, 2, 1, INPUT_SAMPLE_RATE, WHISPER_SAMPLE_RATE, None
        )
        sample_rate = WHISPER_SAMPLE_RATE

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buffer.getvalue()

def preprocess_wav(wav: bytes) -> bytes:
    """Ajusta ganancia y aplica un filtro pasa alto básico."""
    with wave.open(io.BytesIO(wav), "rb") as wf:
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    rms = audioop.rms(frames, 2)
    target = 10000
    gain = target / rms if rms else 1.0

    samples = bytearray()
    prev = 0
    hp = 0.95
    for i in range(0, len(frames), 2):
        sample = int.from_bytes(frames[i:i+2], "little", signed=True)
        sample = int(sample * gain)
        filtered = sample - int(prev * hp)
        prev = sample
        filtered = max(min(filtered, 32767), -32768)
        samples += int(filtered).to_bytes(2, "little", signed=True)

    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(samples))
    return out.getvalue()



def transcribe_chunk(wav: bytes) -> str:
    """Envía audio a Whisper y devuelve el texto."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": ("audio.wav", wav, "audio/wav")}
    data = {"model": "whisper-1", "language": "es"}
    
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
            message = await ws.receive()  # Espera por cualquier tipo de mensaje

            if "text" in message:
                # Twilio Media Streams envía todos los datos como texto JSON
                try:
                    control_data = json.loads(message["text"])
                    event = control_data.get("event")

                    if event == "media":
                        payload_b64 = control_data.get("media", {}).get("payload", "")
                        if payload_b64:
                            buffer += base64.b64decode(payload_b64)

                            while len(buffer) >= CHUNK_SIZE:
                                raw = buffer[:CHUNK_SIZE]
                                buffer = buffer[CHUNK_SIZE:]

                                wav = preprocess_wav(mulaw_to_wav(raw))
                                text = transcribe_chunk(wav)
                                ts_end = time.time()

                                if text and text.strip():
                                    await save_transcript(call_id, ts_start, ts_end, text)
                                    print(f"[{call_id}] Transcribed: {text}")
                                    await ws.send_text(text)

                                ts_start = ts_end

                    elif event == "stop":
                        print(f"[{call_id}] Twilio Media Stream 'stop' event received.")

                        if buffer:
                            print(
                                f"[{call_id}] Processing remaining buffer ({len(buffer)} bytes) before stopping."
                            )
                            wav = preprocess_wav(mulaw_to_wav(buffer))
                            text = transcribe_chunk(wav)
                            ts_end = time.time()
                            if text and text.strip():
                                await save_transcript(call_id, ts_start, ts_end, text)
                                print(f"[{call_id}] Transcribed (final chunk): {text}")

                        stream_active = False
                    else:
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