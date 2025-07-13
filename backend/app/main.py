from fastapi import FastAPI
from fastapi.responses import Response

app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint used by the platform."""
    return {"status": "ok"}


@app.post("/voice")
async def voice():
    """Return a simple greeting for Twilio Voice."""
    twiml = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<Response><Say>Hola, gracias por llamar</Say></Response>"
    )
    return Response(content=twiml, media_type="text/xml")
