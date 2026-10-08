import asyncio

import pytest

from scout.boundaries import RequestBoundary


@pytest.mark.parametrize("length", [None, b"1", b"40000", b"invalid"])
def test_oversized_stream_never_reaches_parser(length):
    calls, responses = [], []
    messages = iter([{"type": "http.request", "body": b"x" * 20000, "more_body": True},
                     {"type": "http.request", "body": b"x" * 20000, "more_body": False}])

    async def app(*args):
        calls.append(True)

    async def receive():
        return next(messages)

    async def send(message):
        responses.append(message)

    asyncio.run(RequestBoundary(app)({"type": "http", "headers": [(b"content-length", length)] if length else []}, receive, send))
    assert not calls
    assert responses[0]["status"] == 413
    assert (b"x-content-type-options", b"nosniff") in responses[0]["headers"]


def test_oversized_api_error_has_security_headers(client):
    response = client.post("/briefs/interpret", content='x' * 40000)
    assert response.status_code == 413
    assert response.headers["x-frame-options"] == "DENY"
