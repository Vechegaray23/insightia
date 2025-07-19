import hashlib
import os
import httpx
import boto3  # Importar boto3
from botocore.client import Config  # Importar Config
from tenacity import retry, stop_after_attempt, wait_random_exponential

# Constants for the TTS configuration
VOICE = os.environ.get("TTS_VOICE", "nova")
MODEL = os.environ.get("TTS_MODEL", "tts-1")

# --- R2 Configuration (UPDATED) ---
# Endpoint URL para R2, debe incluir el ID de cuenta de Cloudflare
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
# Nombre del bucket de R2 donde se guardará el audio
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "mvp-audio")
# Claves de acceso para autenticación S3 (Access Key ID y Secret Access Key de R2)
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

CACHE_PREFIX = "mvp/audio-cache/"

# Inicializar cliente S3 para R2
# Se comprueba que las variables de entorno necesarias estén configuradas.
# Si no lo están, s3_client será None, y las funciones de R2 lanzarán un error.
if all([R2_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
    s3_client = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4') # Esencial para compatibilidad con R2
    )
else:
    s3_client = None # O podrías lanzar un error aquí directamente si R2 es mandatorio

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
        raise RuntimeError("R2 S3 client or bucket name not configured. Check R2_ENDPOINT_URL, R2_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY environment variables.")
    
    # Utiliza put_object de boto3 para subir el archivo a R2
    s3_client.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=data, ContentType="audio/mpeg")


def speak(text: str) -> str:
    """Return the R2 URL for the given text's TTS audio."""
    if not s3_client or not R2_BUCKET_NAME or not R2_ENDPOINT_URL:
        raise RuntimeError("R2 S3 client, bucket name, or endpoint not configured. Check R2_ENDPOINT_URL, R2_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY environment variables.")

    sha = hashlib.sha1(f"{text}{VOICE}{MODEL}".encode()).hexdigest()
    key = f"{CACHE_PREFIX}{sha}.mp3"
    
    # Construir la URL pública correctamente, incluyendo el nombre del bucket
    url = f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/{key}"

    # Comprobar si el objeto existe en R2 usando head_object de boto3
    try:
        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=key)
        return url # Si head_object tiene éxito, el objeto existe, devolver la URL
    except s3_client.exceptions.ClientError as e:
        # Si el error es 404 (Not Found), significa que el objeto no está en el caché
        if e.response['Error']['Code'] == '404':
            pass # Continuar para generar y subir el audio
        else:
            # Re-lanzar cualquier otro error de cliente S3
            raise 

    # Si el audio no está en el caché, generarlo y subirlo
    audio = _fetch_tts_audio(text)
    _upload_to_r2(key, audio)
    return url