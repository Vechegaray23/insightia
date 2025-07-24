# Proyecto Insightia

Proyecto que expone un agente telefónico muy sencillo. A través de Twilio se
recibe audio de una llamada, se genera una respuesta con la API de TTS de
OpenAI y se guarda cada transcripción en Supabase.

## Componentes principales

- `backend`: código en Python con la API y lógica de transcripción.

## Docker

El contenedor se inicia mediante el script `docker-entrypoint.sh`. Este script
reemplaza variables de entorno en `/etc/promtail.yml` con `envsubst`,
ejecuta Promtail y luego arranca el servidor FastAPI con `uvicorn`.

```bash
docker build -t insightia .
docker run --env-file .env -p 8000:8000 insightia
```

La aplicación quedará disponible en `http://localhost:8000`.

## Variables de entorno

- `TWILIO_SAMPLE_RATE`: frecuencia de muestreo del audio recibido por Twilio.
  Si no se define se utilizará `16000` Hz.
- `OPENAI_API_KEY`: clave de API para acceder a la generación de voz y
  transcripciones.
- `SUPABASE_URL` y `SUPABASE_KEY`: datos de la base de datos donde se guardan
  las transcripciones.
- Variables de TTS (`TTS_VOICE`, `TTS_MODEL`) y de almacenamiento en Cloudflare
  R2 (`R2_ENDPOINT_URL`, `R2_BUCKET_NAME`, `R2_PUBLIC_BASE_URL`,
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
