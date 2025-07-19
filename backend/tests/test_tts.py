import hashlib

import asyncio
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
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://r2")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", url_base)
    tts.BUCKET_BASE_URL = url_base
    tts.R2_BUCKET_NAME = "bucket"
    tts.R2_ENDPOINT_URL = "https://r2"
    tts.R2_PUBLIC_BASE_URL = url_base
    tts.R2_BUCKET_NAME = "bucket"
    tts.R2_ENDPOINT_URL = "https://r2"
    tts.R2_PUBLIC_BASE_URL = url_base
    tts.R2_BUCKET_NAME = "bucket"
    tts.R2_ENDPOINT_URL = "https://r2"
    tts.R2_PUBLIC_BASE_URL = url_base

    class Client:
        class exceptions:
            class ClientError(Exception):
                pass

        def head_object(self, Bucket=None, Key=None):
            return True

    tts.s3_client = Client()

    monkeypatch.setattr(httpx, "head", lambda url, headers=None: DummyResp(200))

    async def fake_fetch(text):
        return b"audio"

    async def fake_upload(key, data):
        return None

    monkeypatch.setattr(tts, "_fetch_tts_audio", fake_fetch)
    monkeypatch.setattr(tts, "_upload_to_r2", fake_upload)

    url = asyncio.run(tts.speak("hola"))
    expected_hash = hashlib.sha1(f"hola{tts.VOICE}{tts.MODEL}".encode()).hexdigest()

    assert url == f"{url_base}/{tts.CACHE_PREFIX}{expected_hash}.mp3"


def test_speak_generate(monkeypatch):
    url_base = "https://cache.example.com"
    monkeypatch.setenv("R2_BUCKET_BASE_URL", url_base)
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://r2")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", url_base)
    tts.BUCKET_BASE_URL = url_base
    class DummyS3:
        class exceptions:
            class ClientError(Exception):
                def __init__(self, response=None, operation_name=None):
                    self.response = {"Error": {"Code": "404"}}

        def put_object(self, Bucket=None, Key=None, Body=None, ContentType=None):
            pass

        def head_object(self, Bucket=None, Key=None):
            raise self.exceptions.ClientError({"Error": {"Code": "404"}}, None)

    tts.s3_client = DummyS3()

    calls = {}

    def fake_head(url, headers=None):
        calls["head"] = url
        return DummyResp(404)

    async def fake_fetch(text):
        calls["fetch"] = text
        return b"audio-data"

    async def fake_upload(key, data):
        calls["upload"] = (key, data)

    monkeypatch.setattr(httpx, "head", fake_head)
    monkeypatch.setattr(tts, "_fetch_tts_audio", fake_fetch)
    monkeypatch.setattr(tts, "_upload_to_r2", fake_upload)

    url = asyncio.run(tts.speak("hola"))
    expected_hash = hashlib.sha1(f"hola{tts.VOICE}{tts.MODEL}".encode()).hexdigest()

    key = f"{tts.CACHE_PREFIX}{expected_hash}.mp3"
    assert url == f"{url_base}/{key}"
    assert calls["fetch"] == "hola"
    assert calls["upload"] == (key, b"audio-data")


def test_upload_auth_header(monkeypatch):
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    class DummyS3:
        def __init__(self):
            self.called = False

        def put_object(self, **kwargs):
            self.called = True

    tts.s3_client = DummyS3()
    asyncio.run(tts._upload_to_r2("file.mp3", b"data"))
    assert tts.s3_client.called
