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
                self.text = resp.content
                self.headers = resp.headers
        return Result(response)