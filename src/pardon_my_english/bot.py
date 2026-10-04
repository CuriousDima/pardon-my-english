"""Telegram bot entry point and handlers."""

import logging
import os
import sys
from functools import partial

from dotenv import load_dotenv
from telegram import Message, Update
from telegram.constants import ChatAction, MessageLimit
from telegram.error import BadRequest, NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from pardon_my_english.db import DBClient
from pardon_my_english.llm import LLMClient

logger = logging.getLogger(__name__)

# Environment variables names
_TELEGRAM_BOT_TOKEN_VAR_NAME = "TELEGRAM_BOT_TOKEN"
_DB_URI_VAR_NAME = "DB_URI"

_START_MESSAGE = (
    "Hi there! I'm a bot designed to assist you in rephrasing your text into polished English. "
    "Please type whatever you want to be rewritten, and I'll rework it into proper English for you."
)


def split_message(text: str, limit: int = MessageLimit.MAX_TEXT_LENGTH) -> list[str]:
    """Split text into chunks that fit into a Telegram message.

    Prefers to split between paragraphs, then lines, then words.
    """
    chunks: list[str] = []
    while len(text) > limit:
        for separator in ("\n\n", "\n", " "):
            cut = text.rfind(separator, 0, limit + 1)
            if cut > limit // 2:
                break
        else:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def _get_message(update: Update) -> Message:
    message = update.message or update.edited_message
    assert message is not None, "No message found on the update."
    return message


def _get_user_info(update: Update) -> tuple[int, str | None]:
    user = update.effective_user
    assert user is not None, "No user found on the update."
    return user.id, user.username


async def start_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await _get_message(update).reply_text(_START_MESSAGE)


async def get_model_command(
    update: Update,
    _: ContextTypes.DEFAULT_TYPE,
    db_client: DBClient,
) -> None:
    """Get the current model being used by the user."""
    message = _get_message(update)
    user_id, username = _get_user_info(update)
    account = db_client.get_or_create_account(user_id=user_id, username=username)
    await message.reply_text(
        f"You are currently using {account.model.value} via OpenRouter."
    )


async def rewrite(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_client: DBClient,
    llm_client: LLMClient,
) -> None:
    # Handle the message
    message = _get_message(update)
    input_message = message.text
    assert input_message is not None, "No message to rewrite."
    # Handle the user
    user_id, username = _get_user_info(update)
    account = db_client.get_or_create_account(user_id=user_id, username=username)
    # Check if the user has run out of tokens.
    # If the user is a friend, they have an unlimited token balance. ;)
    if not account.is_friend and account.tokens_balance <= 0:
        await context.bot.send_message(
            chat_id=message.chat_id,
            text="You have run out of tokens. 🥲\n Please contact the bot owner to get more.",
        )
        return
    # Rewrite the message. Do not touch the user's token balance if they are a friend.
    await context.bot.send_chat_action(
        chat_id=message.chat_id, action=ChatAction.TYPING
    )
    rewritten_text, num_tokens = await llm_client.rewrite(
        input_message, model=account.model
    )
    for chunk in split_message(rewritten_text):
        await context.bot.send_message(chat_id=message.chat_id, text=chunk)
    if not account.is_friend:
        db_client.decrease_token_balance(user_id=user_id, num_tokens=num_tokens)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, NetworkError) and not isinstance(
        context.error, BadRequest
    ):
        # Transient Telegram connectivity issues; the library retries on its own.
        # BadRequest subclasses NetworkError but signals a real problem, so it's not skipped.
        logger.warning("Telegram network error: %s", context.error)
        return
    logger.error("Failed to handle an update.", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message is not None:
        await update.effective_message.reply_text(
            "Sorry, something went wrong. 😔 Please try again in a moment."
        )


def _get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        sys.exit(f"{var_name} is not set.")
    return value


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    # httpx logs every Telegram long-polling request at INFO level.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_dotenv()

    db_client = DBClient(db_url=_get_required_env(_DB_URI_VAR_NAME))
    llm_client = LLMClient()

    app = (
        ApplicationBuilder()
        .token(_get_required_env(_TELEGRAM_BOT_TOKEN_VAR_NAME))
        .build()
    )
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(
        CommandHandler("model", partial(get_model_command, db_client=db_client))
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND),
            partial(rewrite, db_client=db_client, llm_client=llm_client),
        )
    )
    app.add_error_handler(error_handler)

    app.run_polling()


if __name__ == "__main__":
    main()
