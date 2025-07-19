class Response:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPStatusError("error", request=None, response=None)


class HTTPStatusError(Exception):
    def __init__(self, message, request=None, response=None):
        super().__init__(message)
        self.request = request
        self.response = response


def head(url, headers=None):
    return Response()


def post(url, headers=None, json=None):
    return Response()


def put(url, content=None, headers=None):
    return Response()


class AsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def post(self, url, headers=None, json=None, files=None):
        return Response()
