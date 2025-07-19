import hashlib
import os
import httpx
import asyncio # Necesario para asyncio.sleep y para que retry funcione con async
try:
    import boto3  # type: ignore
    from botocore.client import Config  # type: ignore
except Exception:  # pragma: no cover - boto3 might not be available
    boto3 = None
    Config = None
from tenacity import retry, stop_after_attempt, wait_random_exponential, AsyncRetrying # Usar AsyncRetrying

# Constants for the TTS configuration
VOICE = os.environ.get("TTS_VOICE", "onyx")
MODEL = os.environ.get("TTS_MODEL", "tts-1")

# --- R2 Configuration (UPDATED) ---
# Endpoint URL para R2 para operaciones autenticadas (boto3)
R2_ENDPOINT_URL = os.environ.get(
    "R2_ENDPOINT_URL"
)
# Nombre del bucket de R2
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "mvp-audio")
# Claves de acceso para autenticación S3 (Access Key ID y Secret Access Key de R2)
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# **NUEVA VARIABLE:** URL base pública para acceder a los archivos.
R2_PUBLIC_BASE_URL = os.environ.get(
    "R2_PUBLIC_BASE_URL", "https://pub-e5143777090b4fd78d88cbbf56013064.r2.dev"
)
CACHE_PREFIX = "tts-cache/"


s3_client = None
if boto3:
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
    except Exception as e:
        print(f"Error initializing R2 S3 client: {e}")
        s3_client = None


# Modificación: Hacer _fetch_tts_audio asíncrona
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
async def _fetch_tts_audio(text: str) -> bytes:
    """Call OpenAI's TTS API and return binary MP3 data."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"model": MODEL, "voice": VOICE, "input": text}
    # Usar httpx.AsyncClient para llamadas HTTP asíncronas
    async with httpx.AsyncClient(timeout=10) as client: # Añadir timeout
        resp = await client.post("https://api.openai.com/v1/audio/speech", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.content

# Modificación: Hacer _upload_to_r2 asíncrona
async def _upload_to_r2(key: str, data: bytes) -> None:
    """Upload MP3 data to Cloudflare R2 using boto3."""
    # En boto3, las operaciones s3_client son generalmente síncronas.
    # Para hacerla "asíncrona" en un contexto FastAPI/asyncio,
    # se suele usar loop.run_in_executor o librerías async-aware como aioboto3.
    # Por simplicidad aquí, la llamaremos directamente, pero ten en cuenta esto en producción.
    # Para una implementación puramente asíncrona, considera 'aioboto3'.
    if s3_client:
        await asyncio.to_thread(s3_client.put_object, Bucket=R2_BUCKET_NAME, Key=key, Body=data, ContentType="audio/mpeg")
    else:
        raise RuntimeError("S3 client not initialized. Cannot upload to R2.")


# Modificación: Hacer speak asíncrona
async def speak(text: str) -> str:
    """Return the R2 URL for the given text's TTS audio."""
    if not all([s3_client, R2_BUCKET_NAME, R2_ENDPOINT_URL, R2_PUBLIC_BASE_URL]):
        raise RuntimeError(
            "R2 configuration incomplete. Check R2_ENDPOINT_URL, R2_BUCKET_NAME, "
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and R2_PUBLIC_BASE_URL "
            "environment variables."
        )

    sha = hashlib.sha1(f"{text}{VOICE}{MODEL}".encode()).hexdigest()
    key = f"{CACHE_PREFIX}{sha}.mp3"

    url = f"{R2_PUBLIC_BASE_URL}/{key}"

    # Comprobar si el objeto existe en R2 usando head_object de boto3
    try:
        if s3_client:
            await asyncio.to_thread(s3_client.head_object, Bucket=R2_BUCKET_NAME, Key=key)
            return url # Si head_object tiene éxito, el objeto existe, devolver la URL pública
        else:
            raise RuntimeError("S3 client not initialized. Cannot check R2.")
    except s3_client.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            pass  # Objeto no encontrado, continuar para generarlo y subirlo
        else:
            raise # Otro error de S3, re-lanzar
    except Exception as e:
        print(f"Error checking R2 cache for key {key}: {e}")
        pass # Si hay un error al verificar la caché, intenta generar de nuevo


    # Si no está en caché, generar y subir
    try:
        mp3_data = await _fetch_tts_audio(text)
        await _upload_to_r2(key, mp3_data)
        print(f"Generated and uploaded TTS for '{text}' to R2: {url}")
        return url
    except Exception as e:
        print(f"Failed to generate or upload TTS for '{text}': {e}")
        raise # Re-lanzar para que el llamador lo maneje (ej. fallback a <Say>)