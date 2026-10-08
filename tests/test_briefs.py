import asyncio

import httpx
import pytest

from scout.briefs import interpret


@pytest.mark.parametrize("content", ['{"role":"CB","extra_sql":"DROP TABLE"}',
                                     '{"role":"CB","preferences":{"invented_speed":5}}',
                                     '{"role":"ST","weights":{"quality":0}}', 'not json'])
def test_invalid_ollama_output_falls_back_to_editable_rules(monkeypatch, content):
    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            assert url == "http://127.0.0.1:11434/api/chat"
            return httpx.Response(200, request=httpx.Request("POST", url), json={"message": {"content": content}})

    monkeypatch.setattr("scout.briefs.httpx.AsyncClient", lambda **kwargs: Client())
    response = asyncio.run(interpret("athletic left-footed CB", True, "local-model"))
    assert response["method"] == "structured_rules"
    assert response["brief"].constraints.foot == "left"
    assert any("invalid" in warning for warning in response["warnings"])
