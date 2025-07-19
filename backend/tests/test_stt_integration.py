from backend.app.main import app
from backend.app import stt
from fastapi.testclient import TestClient


def test_stt_websocket(monkeypatch):
    client = TestClient(app)
    messages = []

    def fake_transcribe(wav: bytes) -> str:
        messages.append("called")
        return "hola"

    monkeypatch.setattr(stt, "transcribe_chunk", fake_transcribe)
    chunk = b"\xff" * stt.CHUNK_SIZE
    with client.websocket_connect("/stt") as ws:
        ws.send_bytes(chunk)

    assert messages == ["called"]
    assert ws.outgoing == ["hola"]
