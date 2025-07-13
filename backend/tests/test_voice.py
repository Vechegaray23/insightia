from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_voice_endpoint():
    response = client.post("/voice")
    assert response.status_code == 200
    assert "<Say>Hola" in response.text
    assert response.headers["content-type"].startswith("text/xml")
