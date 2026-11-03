import tempfile

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import MAX_MULTIPART_OVERHEAD_BYTES, MAX_UPLOAD_BYTES, UPLOAD_CHUNK_BYTES

UPLOAD_PATH = "/api/requirements"
MAX_UPLOAD_REQUEST_BYTES = MAX_UPLOAD_BYTES + MAX_MULTIPART_OVERHEAD_BYTES


class UploadRequestLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != UPLOAD_PATH:
            await self.app(scope, receive, send)
            return

        with tempfile.TemporaryFile() as body:
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > MAX_UPLOAD_REQUEST_BYTES:
                    response = JSONResponse(status_code=413, content={"detail": "Request too large"})
                    await response(scope, receive, send)
                    return
                body.write(chunk)
                if not message.get("more_body", False):
                    break
            body.seek(0)
            remaining = size

            async def replay() -> Message:
                nonlocal remaining
                if remaining == 0:
                    return {"type": "http.request", "body": b"", "more_body": False}
                chunk = body.read(min(remaining, UPLOAD_CHUNK_BYTES))
                remaining -= len(chunk)
                return {"type": "http.request", "body": chunk, "more_body": remaining > 0}

            await self.app(scope, replay, send)
