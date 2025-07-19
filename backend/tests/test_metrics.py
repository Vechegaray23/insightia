from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_metrics_endpoint(monkeypatch):
    response = client.post("/wer", {"reference": "hola", "hypothesis": "hola"})
    assert response.status_code == 200
    data = client.get("/metrics").json()
    assert list(data.values())[0] == 0.0
