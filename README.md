# Proyecto Insightia

Servicio mínimo para recibir llamadas vía Twilio, hablar con TTS y guardar las transcripciones en Supabase.

## Componentes principales

- `backend`: código en Python con la API y lógica de transcripción.

## Docker

El contenedor se inicia mediante el script `docker-entrypoint.sh`. Este script
reemplaza variables de entorno en `/etc/promtail.yml` con `envsubst`,
ejecuta Promtail y luego arranca el servidor FastAPI con `uvicorn`.

## Variables de entorno

- `TWILIO_SAMPLE_RATE`: frecuencia de muestreo del audio recibido por Twilio.
  Si no se define, el backend utilizará `8000` Hz por defecto.
