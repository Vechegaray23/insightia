from fastapi import FastAPI
from fastapi.responses import Response

from .tts import speak
from . import stt, wer

app = FastAPI()


@app.websocket("/stt")
def websocket_stt(ws):
    """Recibir audio μ-law y devolver texto."""
    call_id = "test-call"
    stt.process_stream(ws, call_id)


@app.post("/wer")
def calc_wer(payload: dict) -> dict:
    """Calcular WER entre referencia e hipótesis y registrar."""
    ref = payload.get("reference", "")
    hyp = payload.get("hypothesis", "")
    score = wer.wer(ref, hyp)
    wer.metrics.add(score)
    return {"wer": score}


@app.get("/metrics")
def metrics():
    """Obtener métricas de WER diarias."""
    return wer.metrics.metrics()


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint used by the platform."""
    return {"status": "ok"}


@app.post("/voice")
async def voice():
    """Return TwiML that plays a cached TTS greeting."""
    text = "En un bosque mágico, un pequeño conejo encontró una estrella fugaz. Pidió un deseo: ¡chocolate infinito! Y así, el bosque se llenó de dulces sonrisas."
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

