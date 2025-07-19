from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import tts

client = TestClient(app)


def test_voice_endpoint(monkeypatch):
    monkeypatch.setattr(tts, "speak", lambda text: "https://audio/file.mp3")
    monkeypatch.setattr(
        "backend.app.main.speak",
        lambda text: "https://audio/file.mp3",
        raising=False,
    )
    response = client.post("/voice")
    assert response.status_code == 200
    assert "<Play>https://audio/file.mp3</Play>" in response.text
    assert response.headers["content-type"].startswith("text/xml")


def test_voice_endpoint_fallback(monkeypatch):
    def fail_speak(text: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(tts, "speak", fail_speak)
    monkeypatch.setattr("backend.app.main.speak", fail_speak, raising=False)

    response = client.post("/voice")
    assert response.status_code == 200
    assert "<Say>" in response.text
    assert response.headers["content-type"].startswith("text/xml")
