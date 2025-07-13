class Response:
    def __init__(self, content: str, media_type: str = "text/plain"):
        self.content = content
        self.text = content
        self.headers = {"content-type": media_type}