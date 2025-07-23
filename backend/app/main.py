# backend/app/main.py (VERSIÓN DE TEST CON HARDCODEO)

import os
import json
import traceback
from fastapi import FastAPI, Response, WebSocket
from . import stt, wer # Se quita la importación de tts

app = FastAPI()

# --- WebSocket Endpoint (Sin cambios) ---
@app.websocket("/stt")
async def websocket_stt(websocket: WebSocket):
    await websocket.accept()
    call_id = None
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event = data.get("event")
            if event == "start":
                call_id = data.get("start", {}).get("callSid")
                break
        if not call_id: raise RuntimeError("No se pudo obtener call_id.")
        await stt.process_stream(websocket, call_id)
    except Exception as e:
        print(f"ERROR CRÍTICO en WebSocket: {e}\n{traceback.format_exc()}")
    finally:
        print(f"Manejador de WebSocket finalizado para llamada: {call_id or 'unknown'}")


# --- TwiML Endpoint (MODIFICADO PARA EL TEST) ---
@app.post("/voice")
async def voice():
    """
    Devuelve TwiML hardcodeado para eliminar toda variabilidad y aislar el problema.
    """
    print("VOICE: Endpoint /voice activado (TEST DE HARDCODEO DEFINITIVO).")

    websocket_url = os.environ.get("TWILIO_WEBSOCKET_URL")
    if not websocket_url:
        return Response(content="Error: TWILIO_WEBSOCKET_URL no configurado.", status_code=500)

    # --- TwiML COMPLETAMENTE ESTÁTICO ---
    # No hay llamadas a TTS. No hay variables. Solo una cadena de texto pura.
    twiml_static_string = f"""<?xml version='1.0' encoding='UTF-8'?>
<Response>
  <Start>
    <Stream url='{websocket_url}' />
  </Start>
  <Say>Esto es una prueba de saludo estático.</Say>
  <Pause length='60'/>
</Response>"""

    print(f"VOICE: TwiML generado (HARDCODEADO):\n{twiml_static_string}")
    return Response(content=twiml_static_string, media_type="text/xml")


# --- Endpoints de Soporte (Sin cambios) ---
@app.get("/health")
async def health(): return {"status": "ok"}