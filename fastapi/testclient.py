import asyncio
import inspect
from typing import Any


class TestClient:

    __test__ = False

    def __init__(self, app: Any):
        self.app = app

    def post(self, path: str, data: Any = None):
        handler = self.app.routes.get(("POST", path))
        if handler is None:
            raise ValueError(f"No route for POST {path}")
        if inspect.iscoroutinefunction(handler):
            response = asyncio.run(handler(data)) if data is not None else asyncio.run(handler())
        else:
            response = handler(data) if data is not None else handler()

        class Result:
            def __init__(self, resp):
                self.status_code = 200
                self.text = getattr(resp, "content", resp)
                self.headers = getattr(resp, "headers", {})
                self._resp = resp

        return Result(response)

    class _WSConn:
        def __init__(self, handler):
            self.handler = handler
            self.incoming = []
            self.outgoing = []

        def send_bytes(self, data: bytes) -> None:
            self.incoming.append(data)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            async def run():
                class FakeWS:
                    def __init__(self, incoming, outgoing):
                        self._in = incoming
                        self._out = outgoing

                    def receive_bytes(self):
                        if self._in:
                            return self._in.pop(0)
                        return b""

                    def send_text(self, text: str):
                        self._out.append(text)

                ws = FakeWS(self.incoming, self.outgoing)
                if inspect.iscoroutinefunction(self.handler):
                    await self.handler(ws)
                else:
                    self.handler(ws)

            asyncio.run(run())

    def websocket_connect(self, path: str):
        handler = self.app.routes.get(("WS", path))
        if handler is None:
            raise ValueError(f"No route for WS {path}")
        return self._WSConn(handler)

    def get(self, path: str):
        handler = self.app.routes.get(("GET", path))
        if handler is None:
            raise ValueError(f"No route for GET {path}")
        if inspect.iscoroutinefunction(handler):
            response = asyncio.run(handler())
        else:
            response = handler()

        class Result:
            def __init__(self, resp):
                self.status_code = 200
                self.text = getattr(resp, "content", resp)
                self.headers = getattr(resp, "headers", {})
                self._resp = resp

            def json(self):
                return self._resp

        return Result(response)
