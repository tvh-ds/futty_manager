"""Bound HTTP bodies before parsing and secure rejection responses."""
from starlette.responses import JSONResponse

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class RequestBoundary:
    def __init__(self, app, limit=32768):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def secured_send(message):
            if message["type"] == "http.response.start":
                names = {name.lower().encode() for name in SECURITY_HEADERS}
                headers = [(key, value) for key, value in message.get("headers", []) if key.lower() not in names]
                message = {**message, "headers": headers + [(key.lower().encode(), value.encode())
                           for key, value in SECURITY_HEADERS.items()]}
            await send(message)

        length = dict(scope.get("headers", [])).get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > self.limit):
            return await JSONResponse({"detail": "Request body is too large"}, status_code=413)(scope, receive, secured_send)
        content = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(content) + len(chunk) > self.limit:
                return await JSONResponse({"detail": "Request body is too large"}, status_code=413)(scope, receive, secured_send)
            content.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(content), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, secured_send)
