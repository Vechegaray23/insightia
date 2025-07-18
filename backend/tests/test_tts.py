import hashlib

import httpx

from backend.app import tts


class DummyResp:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


def test_speak_cached(monkeypatch):
    url_base = "https://cache.example.com"
    monkeypatch.setenv("R2_BUCKET_BASE_URL", url_base)
    tts.BUCKET_BASE_URL = url_base

    class Client:
        def head(self, url):
            assert url.startswith(url_base)
            return DummyResp(200)

    monkeypatch.setattr(httpx, "head", lambda url: DummyResp(200))
    monkeypatch.setattr(tts, "_fetch_tts_audio", lambda text: b"audio")
    monkeypatch.setattr(tts, "_upload_to_r2", lambda key, data: None)

    url = tts.speak("hola")
    expected_hash = hashlib.sha1(f"hola{tts.VOICE}{tts.MODEL}".encode()).hexdigest()

    assert url == f"{url_base}/{tts.CACHE_PREFIX}{expected_hash}.mp3"


def test_speak_generate(monkeypatch):
    url_base = "https://cache.example.com"
    monkeypatch.setenv("R2_BUCKET_BASE_URL", url_base)
    tts.BUCKET_BASE_URL = url_base

    calls = {}

    def fake_head(url):
        calls["head"] = url
        return DummyResp(404)

    def fake_fetch(text):
        calls["fetch"] = text
        return b"audio-data"

    def fake_upload(key, data):
        calls["upload"] = (key, data)

    monkeypatch.setattr(httpx, "head", fake_head)
    monkeypatch.setattr(tts, "_fetch_tts_audio", fake_fetch)
    monkeypatch.setattr(tts, "_upload_to_r2", fake_upload)

    url = tts.speak("hola")
    expected_hash = hashlib.sha1(f"hola{tts.VOICE}{tts.MODEL}".encode()).hexdigest()

    key = f"{tts.CACHE_PREFIX}{expected_hash}.mp3"
    assert url == f"{url_base}/{key}"
    assert calls["fetch"] == "hola"
    assert calls["upload"] == (key, b"audio-data")
