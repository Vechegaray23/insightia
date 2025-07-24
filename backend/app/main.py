import os
from fastapi import FastAPI, Response

app = FastAPI()

@app.post("/voice")
async def voice():
    # TwiML que saluda, graba la llamada y pide transcripción
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <!-- 1) Saludo con TTS nativo de Twilio -->
  <Say voice="alice" language="es-CL">
    Hola, bienvenido. Por favor, dime lo que desees grabar.
  </Say>

  <!-- 2) Graba todo el audio (inbound+outbound) y transcribe -->
  <Record
    maxLength="120"
    transcribe="true"
    recordingTrack="both_tracks"
  />
</Response>
"""
    return Response(content=twiml, media_type="text/xml")
