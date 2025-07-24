# Backend

Contiene la aplicación FastAPI que ofrece los endpoints usados por Twilio para
la recepción y transcripción del audio.

## Uso en desarrollo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Estructura

- `app/main.py`: define la API y las rutas principales.
- `app/stt.py`: utilidades para convertir audio μ‑law a WAV y enviar los
  fragmentos a Whisper.
- `app/tts.py`: genera audio con la API de OpenAI y lo guarda en Cloudflare R2.
- `app/supabase.py`: almacena las transcripciones en Supabase cuando existen
  credenciales.

