# Proyecto Insightia

Este repositorio contiene la infraestructura y código inicial del MVP para un agente telefónico con IA.

## Repositorios internos

- `iac`: Terraform para la infraestructura.
- `backend`: código en Python y pruebas.
- `frontend`: interfaz de usuario.

## Docker

El contenedor se inicia mediante el script `docker-entrypoint.sh`. Este script
reemplaza variables de entorno en `/etc/promtail.yml` con `envsubst`,
ejecuta Promtail y luego arranca el servidor FastAPI con `uvicorn`.

## Variables de entorno

- `TWILIO_SAMPLE_RATE`: frecuencia de muestreo del audio recibido por Twilio.
  Si no se define, el backend utilizará `8000` Hz por defecto.
