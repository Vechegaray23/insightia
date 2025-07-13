
from typing import Callable, Dict, Tuple

# Re-export key helpers to mimic the real package structure
from . import testclient, responses

__all__ = ["FastAPI", "Response", "testclient", "responses"]


class Response:
    def __init__(self, content: str, media_type: str = "text/plain"):
        self.content = content
        self.text = content
        self.headers = {"content-type": media_type}

class FastAPI:
    def __init__(self):
        self.routes: Dict[Tuple[str, str], Callable] = {}

    def post(self, path: str):
        def decorator(func: Callable):
            self.routes[("POST", path)] = func
            return func
        return decorator

# Submodule-style exports are already imported above so users can access
# `fastapi.testclient` and `fastapi.responses`.