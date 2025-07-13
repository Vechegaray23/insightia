import asyncio
import inspect
from typing import Any


class TestClient:
    def __init__(self, app: Any):
        self.app = app

    def post(self, path: str):
        handler = self.app.routes.get(("POST", path))
        if handler is None:
            raise ValueError(f"No route for POST {path}")
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

        return Result(response)

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
