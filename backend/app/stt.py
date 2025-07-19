"""Utilidades de STT con Whisper."""

import audioop
import io
import os
import time
import wave

import httpx

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
    resp = httpx.post(
        "https://api.openai.com/v1/audio/transcriptions", headers=headers, data=data, files=files
    )
    resp.raise_for_status()
    return resp.json().get("text", "")


def process_stream(ws, call_id: str) -> None:
    """Procesa audio por WebSocket y emite transcripciones."""
    buffer = b""
    ts_start = time.time()
    while True:
        chunk = ws.receive_bytes()
        if not chunk:
            break
        buffer += chunk
        while len(buffer) >= CHUNK_SIZE:
            raw = buffer[:CHUNK_SIZE]
            buffer = buffer[CHUNK_SIZE:]
            wav = mulaw_to_wav(raw)
            text = transcribe_chunk(wav)
            ts_end = time.time()
            save_transcript(call_id, ts_start, ts_end, text)
            ws.send_text(text)
            ts_start = ts_end

