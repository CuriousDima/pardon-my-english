from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Update
from telegram.error import BadRequest, NetworkError

from pardon_my_english.bot import error_handler, rewrite, split_message
from pardon_my_english.db import DBClient
from pardon_my_english.llm import Model, Provider


def test_split_message_keeps_short_text_intact() -> None:
    assert split_message("Hello!") == ["Hello!"]
    assert split_message("") == []


def test_split_message_prefers_paragraphs_then_words() -> None:
    text = "a" * 60 + "\n\n" + "b " * 30 + "c" * 50
    chunks = split_message(text, limit=100)
    assert chunks[0] == "a" * 60
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "").replace("\n", "")


def test_split_message_hard_cuts_without_separators() -> None:
    assert split_message("x" * 250, limit=100) == ["x" * 100, "x" * 100, "x" * 50]


class FakeLLMClient:
    """Stands in for LLMClient; typed as Any where passed to the handler."""

    def __init__(self, text: str, tokens: int) -> None:
        self.result = (text, tokens)
        self.calls: list[tuple[str, Provider, Model]] = []

    async def rewrite(
        self, text: str, provider: Provider, model: Model
    ) -> tuple[str, int]:
        self.calls.append((text, provider, model))
        return self.result


def _make_update(text: str, user_id: int = 42) -> Any:
    update = MagicMock()
    update.message.text = text
    update.message.chat_id = 100
    update.effective_user.id = user_id
    update.effective_user.username = "user"
    return update


def _make_context() -> Any:
    return SimpleNamespace(
        bot=SimpleNamespace(send_message=AsyncMock(), send_chat_action=AsyncMock())
    )


@pytest.fixture
def db(tmp_path) -> DBClient:
    return DBClient(str(tmp_path / "accounts.db"))


@pytest.mark.anyio
async def test_rewrite_replies_and_charges_tokens(db: DBClient) -> None:
    context = _make_context()
    llm_client: Any = FakeLLMClient("He went home.", tokens=100)

    await rewrite(
        _make_update("he go home"), context, db_client=db, llm_client=llm_client
    )

    assert llm_client.calls == [("he go home", Provider.OPENROUTER, Model.GPT6_LUNA)]
    context.bot.send_message.assert_awaited_once_with(chat_id=100, text="He went home.")
    assert db.get_or_create_account(user_id=42).tokens_balance == 999_900


@pytest.mark.anyio
async def test_rewrite_does_not_charge_friends(db: DBClient) -> None:
    db.get_or_create_account(user_id=42)
    with db.engine.begin() as connection:
        connection.exec_driver_sql("UPDATE account SET is_friend = 1")

    await rewrite(
        _make_update("hi"),
        _make_context(),
        db_client=db,
        llm_client=cast(Any, FakeLLMClient("Hi!", tokens=100)),
    )

    assert db.get_or_create_account(user_id=42).tokens_balance == 1_000_000


@pytest.mark.anyio
async def test_rewrite_refuses_when_out_of_tokens(db: DBClient) -> None:
    db.get_or_create_account(user_id=42)
    db.decrease_token_balance(user_id=42, num_tokens=1_000_000)
    context = _make_context()
    llm_client: Any = FakeLLMClient("unused", tokens=0)

    await rewrite(_make_update("hi"), context, db_client=db, llm_client=llm_client)

    assert llm_client.calls == []
    assert "run out of tokens" in context.bot.send_message.await_args.kwargs["text"]


@pytest.mark.anyio
async def test_error_handler_ignores_network_errors() -> None:
    context: Any = SimpleNamespace(error=NetworkError("Server disconnected"))
    await error_handler(None, context)


@pytest.mark.anyio
async def test_error_handler_apologizes_for_other_errors() -> None:
    update = MagicMock(spec=Update)
    update.effective_message.reply_text = AsyncMock()
    context: Any = SimpleNamespace(error=BadRequest("Message is too long"))

    await error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once()
