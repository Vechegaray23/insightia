import hashlib
import os
import httpx
import boto3  # Importar boto3
from botocore.client import Config  # Importar Config
from tenacity import retry, stop_after_attempt, wait_random_exponential

# Constants for the TTS configuration
VOICE = os.environ.get("TTS_VOICE", "onyx")
MODEL = os.environ.get("TTS_MODEL", "tts-1-hd")

# --- R2 Configuration (UPDATED) ---
# Endpoint URL para R2 para operaciones autenticadas (boto3)
R2_ENDPOINT_URL = os.environ.get(
    "R2_ENDPOINT_URL"
)  # e.g., https://<ACCOUNT_ID>.r2.cloudflarestorage.com
# Nombre del bucket de R2
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "mvp-audio")
# Claves de acceso para autenticación S3 (Access Key ID y Secret Access Key de R2)
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# **NUEVA VARIABLE:** URL base pública para acceder a los archivos.
# Esto es lo que acabas de compartir: https://pub-e5143777090b4fd78d88cbbf56013064.r2.dev
R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL")


CACHE_PREFIX = "mvp/audio-cache/"

# Inicializar cliente S3 para R2
if all([R2_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
    s3_client = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),  # Esencial para compatibilidad con R2
    )
else:
    s3_client = None


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
    """Upload MP3 data to Cloudflare R2 using boto3."""
    if not s3_client or not R2_BUCKET_NAME:
        raise RuntimeError(
            "R2 S3 client or bucket name not configured. Check R2_ENDPOINT_URL, "
            "R2_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY "
            "environment variables."
        )

    s3_client.put_object(
        Bucket=R2_BUCKET_NAME, Key=key, Body=data, ContentType="audio/mpeg"
    )


def speak(text: str) -> str:
    """Return the R2 URL for the given text's TTS audio."""
    # Asegurarse de que todas las variables de entorno necesarias estén configuradas
    if not all([s3_client, R2_BUCKET_NAME, R2_ENDPOINT_URL, R2_PUBLIC_BASE_URL]):
        raise RuntimeError(
            "R2 configuration incomplete. Check R2_ENDPOINT_URL, R2_BUCKET_NAME, "
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and R2_PUBLIC_BASE_URL "
            "environment variables."
        )

    sha = hashlib.sha1(f"{text}{VOICE}{MODEL}".encode()).hexdigest()
    key = f"{CACHE_PREFIX}{sha}.mp3"

    # Construir la URL para acceso público
    # NOTA: La URL pública ya incluye el bucket name
    url = f"{R2_PUBLIC_BASE_URL}/{key}"

    # Comprobar si el objeto existe en R2 usando head_object de boto3 
    # (operación autenticada)
    try:
        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=key)
        # Si head_object tiene éxito, el objeto existe, devolver la URL pública
        return url
    except s3_client.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            pass  # Objeto no encontrado, continuar para generar y subir
        else:
            raise  # Re-lanzar otros errores

    # Generar y subir el audio si no está en el caché
    audio = _fetch_tts_audio(text)
    _upload_to_r2(key, audio)

    # Devolver la URL pública después de subir
    return url
