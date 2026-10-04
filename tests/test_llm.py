import json

import httpx2
import pytest
from openai import AsyncOpenAI

from pardon_my_english import llm
from pardon_my_english.llm import LLMClient, Model, Provider


def _make_client(content: str | None, requests: list[dict]) -> LLMClient:
    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )

    openai_client = AsyncOpenAI(
        base_url="https://llm.test/v1",
        api_key="test",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )
    return LLMClient(clients={Provider.OPENROUTER: openai_client})


@pytest.mark.anyio
async def test_rewrite_sends_delimited_text_and_returns_tokens() -> None:
    requests: list[dict] = []
    client = _make_client("  He and I went to the store.  ", requests)

    text, tokens = await client.rewrite(
        "me and him goes to store", Provider.OPENROUTER, Model.GPT6_LUNA
    )

    assert (text, tokens) == ("He and I went to the store.", 15)
    [request] = requests
    assert request["model"] == "openai/gpt-6-luna"
    assert request["reasoning"] == {"effort": "minimal"}
    assert request["messages"][1] == {
        "role": "user",
        "content": "<text>\nme and him goes to store\n</text>",
    }


@pytest.mark.anyio
async def test_rewrite_strips_echoed_tags() -> None:
    client = _make_client("<text>\nHello there!\n</text>", [])
    text, _ = await client.rewrite("hello their", Provider.OPENROUTER, Model.GPT6_LUNA)
    assert text == "Hello there!"


@pytest.mark.anyio
@pytest.mark.parametrize("content", [None, "", "<text></text>"])
async def test_rewrite_rejects_empty_response(content: str | None) -> None:
    client = _make_client(content, [])
    with pytest.raises(ValueError, match="Empty response"):
        await client.rewrite("hi", Provider.OPENROUTER, Model.GPT6_LUNA)


@pytest.mark.anyio
async def test_rewrite_rejects_invalid_combination() -> None:
    client = _make_client("unused", [])
    with pytest.raises(ValueError, match="Invalid provider-model combination"):
        await client.rewrite("hi", Provider.OPENROUTER, Model.QWEN25_CODER_1_5B)


def test_openrouter_api_key_falls_back_to_openrouter_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_KEY", "fallback")
    assert llm._get_openrouter_api_key() == "fallback"

    monkeypatch.setenv("OPENROUTER_API_KEY", "primary")
    assert llm._get_openrouter_api_key() == "primary"


def test_openrouter_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for var_name in llm.OPENROUTER_API_KEY_VAR_NAMES:
        monkeypatch.delenv(var_name, raising=False)
    with pytest.raises(ValueError, match="is set"):
        llm._get_openrouter_api_key()
