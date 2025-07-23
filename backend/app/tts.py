import hashlib
import os
import asyncio
import json # Necesario para cargar las credenciales JSON desde la variable de entorno
try:
    import boto3
    from botocore.client import Config
except Exception:  # pragma: no cover - boto3 might not be available
    boto3 = None
    Config = None
from tenacity import retry, stop_after_attempt, wait_random_exponential

# Importar las bibliotecas de Google Cloud
from google.cloud import texttospeech_v1beta1 as texttospeech # Usar v1beta1 para WaveNet, etc.
from google.oauth2 import service_account

# Constants for the TTS configuration (Google Cloud specific)
# Elige una voz WaveNet de alta calidad para español (es-ES)
# Puedes ver la lista completa en la documentación de Google Cloud Text-to-Speech
# Ejemplo: es-ES-Wavenet-C (femenina), es-ES-Wavenet-B (masculina)
TTS_VOICE_NAME = os.environ.get("TTS_VOICE_NAME", "es-ES-Wavenet-C")
# Formato de audio para la salida. MP3 es bueno para almacenamiento y reproducción web/Twilio.
TTS_AUDIO_ENCODING = os.environ.get("TTS_AUDIO_ENCODING", "MP3")
# Frecuencia de muestreo. Generar a 16kHz es un buen balance. Twilio hará downsampling a 8kHz.
TTS_SAMPLE_RATE_HERTZ = int(os.environ.get("TTS_SAMPLE_RATE_HERTZ", "16000"))


# Configuración de Google Cloud
# Cargar las credenciales JSON desde una variable de entorno
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

# Inicializar cliente de Google Cloud Text-to-Speech una vez
tts_client = None
try:
    if GOOGLE_APPLICATION_CREDENTIALS_JSON:
        credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
    else:
        tts_client = texttospeech.TextToSpeechClient()
    print("Google TTS Client initialized successfully.")
except Exception as e:
    print(f"Error initializing Google TTS Client: {e}")
    tts_client = None


# --- R2 Configuration (sin cambios, ya que es independiente del proveedor de TTS) ---
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "mvp-audio")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL", "https://pub-e5143777090b4fd78d88cbbf56013064.r2.dev")
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
        print("R2 S3 Client initialized successfully.")
    except Exception as e:
        print(f"Error initializing R2 S3 client: {e}")
        s3_client = None


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
async def _fetch_tts_audio(text: str) -> bytes:
    """Llama a la API de Google Cloud TTS y devuelve los datos binarios de audio."""
    if not tts_client:
        raise RuntimeError("Google TTS Client not initialized. Cannot fetch audio.")

    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Configuración de la voz
    voice_params = texttospeech.VoiceSelectionParams(
        language_code="es-ES", # Asegúrate de que coincida con la voz seleccionada
        name=TTS_VOICE_NAME,
        # ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL # Opcional: FEMALE, MALE, NEUTRAL
    )

    # Configuración del formato de audio
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding[TTS_AUDIO_ENCODING], # Usa el encoding de la variable de entorno
        sample_rate_hertz=TTS_SAMPLE_RATE_HERTZ, # Usa la frecuencia de la variable de entorno
    )

    try:
        # Realizar la solicitud de síntesis.
        # asyncio.to_thread se usa para ejecutar la llamada síncrona de gRPC en un thread separado,
        # para no bloquear el bucle de eventos principal de asyncio.
        response = await asyncio.to_thread(
            tts_client.synthesize_speech,
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        print(f"Error calling Google Cloud TTS API for text '{text}': {e}")
        raise # Re-lanzar para que tenacity lo maneje


async def _upload_to_r2(key: str, data: bytes) -> None:
    """Sube los datos de audio a Cloudflare R2 usando boto3."""
    if not s3_client:
        raise RuntimeError("S3 client not initialized. Cannot upload to R2.")
    try:
        # Al igual que con TTS, usamos asyncio.to_thread para la operación síncrona de boto3
        await asyncio.to_thread(s3_client.put_object, Bucket=R2_BUCKET_NAME, Key=key, Body=data, ContentType="audio/mpeg")
    except Exception as e:
        print(f"Error uploading to R2 for key {key}: {e}")
        raise


async def speak(text: str) -> str:
    """Devuelve la URL de R2 para el audio TTS del texto dado, usando caché."""
    if not all([s3_client, R2_BUCKET_NAME, R2_ENDPOINT_URL, R2_PUBLIC_BASE_URL, tts_client]):
        raise RuntimeError(
            "Configuración de R2 o Google TTS incompleta. "
            "Verifica variables de entorno o la inicialización de clientes."
        )

    # El hash debe incluir la voz, el encoding y la frecuencia de muestreo
    # para asegurar que el caché sea correcto para diferentes configuraciones de TTS.
    sha = hashlib.sha1(
        f"{text}{TTS_VOICE_NAME}{TTS_AUDIO_ENCODING}{TTS_SAMPLE_RATE_HERTZ}".encode()
    ).hexdigest()
    # Asumimos que siempre guardamos en MP3 en R2, ajusta si guardas otro formato
    key = f"{CACHE_PREFIX}{sha}.mp3"

    url = f"{R2_PUBLIC_BASE_URL}/{key}"

    # Comprobar si el objeto existe en R2 usando head_object de boto3
    try:
        if s3_client:
            # Usamos asyncio.to_thread para esta llamada síncrona
            await asyncio.to_thread(s3_client.head_object, Bucket=R2_BUCKET_NAME, Key=key)
            print(f"TTS audio found in R2 cache for '{text}': {url}")
            return url # Si head_object tiene éxito, el objeto existe, devolver la URL pública
        else:
            raise RuntimeError("S3 client not initialized. Cannot check R2 cache.")
    except s3_client.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            print(f"TTS audio not found in R2 cache for '{text}'. Generating...")
            pass  # Objeto no encontrado, continuar para generarlo y subirlo
        else:
            print(f"Error checking R2 cache for key {key}: {e}")
            raise # Otro error de S3, re-lanzar
    except Exception as e:
        print(f"Unexpected error checking R2 cache for key {key}: {e}")
        # En caso de error inesperado al verificar la caché, intenta generar de nuevo
        pass


    # Si no está en caché o hubo un error al verificar, generar y subir
    try:
        mp3_data = await _fetch_tts_audio(text)
        await _upload_to_r2(key, mp3_data)
        print(f"Generated and uploaded TTS for '{text}' to R2: {url}")
        return url
    except Exception as e:
        print(f"Failed to generate or upload TTS for '{text}': {e}")
        raise # Re-lanzar para que el llamador lo maneje (ej. fallback a <Say>)