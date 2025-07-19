from fastapi import FastAPI
from fastapi.responses import Response

from .tts import speak

app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint used by the platform."""
    return {"status": "ok"}


@app.post("/voice")
async def voice():
    """Return TwiML that plays a cached TTS greeting."""
    text = "Hola, gracias por llamar, eres un puto genio"
    try:
        url = speak(text)
        twiml = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            f"<Response><Play>{url}</Play></Response>"
        )
    except Exception:
        twiml = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            f"<Response><Say>{text}</Say></Response>"
        )
    return Response(content=twiml, media_type="text/xml")
