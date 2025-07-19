from typing import Callable, Dict, Tuple

# Re-export key helpers to mimic the real package structure
from . import testclient, responses

__all__ = ["FastAPI", "Response", "WebSocket", "testclient", "responses"]


class Response:
    def __init__(self, content: str, media_type: str = "text/plain"):
        self.content = content
        self.text = content
        self.headers = {"content-type": media_type}


class WebSocket:
    async def accept(self) -> None:  # pragma: no cover - stub
        pass

    async def receive_json(self):  # pragma: no cover - stub
        pass

    async def receive(self):  # pragma: no cover - stub
        pass

    async def send_text(self, data: str) -> None:  # pragma: no cover - stub
        pass


class FastAPI:
    def __init__(self):
        self.routes: Dict[Tuple[str, str], Callable] = {}

    def post(self, path: str):
        def decorator(func: Callable):
            self.routes[("POST", path)] = func
            return func

        return decorator

    def websocket(self, path: str):
        def decorator(func: Callable):
            self.routes[("WS", path)] = func
            return func

        return decorator

    def get(self, path: str):
        def decorator(func: Callable):
            self.routes[("GET", path)] = func
            return func

        return decorator


# Submodule-style exports are already imported above so users can access
# `fastapi.testclient` and `fastapi.responses`.
