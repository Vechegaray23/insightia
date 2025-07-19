from backend.app.main import app
from backend.app import stt
from fastapi.testclient import TestClient
import base64
import json


def test_stt_websocket(monkeypatch):
    client = TestClient(app)
    messages = []

    def fake_transcribe(wav: bytes) -> str:
        messages.append("called")
        return "hola"

    monkeypatch.setattr(stt, "transcribe_chunk", fake_transcribe)
    chunk = b"\xff" * stt.CHUNK_SIZE
    payload = base64.b64encode(chunk).decode()
    with client.websocket_connect("/stt") as ws:
        ws.send_text(json.dumps({"event": "start"}))
        ws.send_text(json.dumps({"event": "media", "media": {"payload": payload}}))
        ws.send_text(json.dumps({"event": "stop"}))

    assert messages == ["called"]
    assert ws.outgoing == ["hola"]
