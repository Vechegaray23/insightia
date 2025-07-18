import hashlib
import os

import httpx
from tenacity import retry, stop_after_attempt, wait_random_exponential

# Constants for the TTS configuration
VOICE = os.environ.get("TTS_VOICE", "nova")
MODEL = os.environ.get("TTS_MODEL", "tts-1")
BUCKET_BASE_URL = os.environ.get("R2_BUCKET_BASE_URL", "https://r2.example.com")
API_TOKEN = os.environ.get("R2_API_TOKEN")

CACHE_PREFIX = "mvp/audio-cache/"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, max=4),
    reraise=True,
)
def _fetch_tts_audio(text: str) -> bytes:
    """Call OpenAI's TTS API and return binary MP3 data."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    headers = {"Authorization": f"Bearer {api_key}"}
    json = {
        "model": MODEL,
        "input": text,
        "voice": VOICE,
        "response_format": "mp3",
    }
    response = httpx.post(
        "https://api.openai.com/v1/audio/speech",
        headers=headers,
        json=json,
    )
    response.raise_for_status()
    return response.content


@retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, max=4),
    reraise=True,
)
def _upload_to_r2(key: str, data: bytes) -> None:
    """Upload MP3 data to Cloudflare R2."""
    url = f"{BUCKET_BASE_URL}/{key}"
    headers = {"Content-Type": "audio/mpeg"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    resp = httpx.put(url, content=data, headers=headers)    
    resp.raise_for_status()


def speak(text: str) -> str:
    """Return the R2 URL for the given text's TTS audio."""
    sha = hashlib.sha1(f"{text}{VOICE}{MODEL}".encode()).hexdigest()
    key = f"{CACHE_PREFIX}{sha}.mp3"
    url = f"{BUCKET_BASE_URL}/{key}"

    headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else None
    head = httpx.head(url) if headers is None else httpx.head(url, headers=headers)    
    if head.status_code == 200:
        return url

    audio = _fetch_tts_audio(text)
    _upload_to_r2(key, audio)
    return url
