from functools import partial
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    filters,
    MessageHandler,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.llm_client import LLMClient
from db_client import DBClient


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
load_dotenv()

# Environment variables names
_TELEGRAM_BOT_TOKEN_VAR_NAME = "TELEGRAM_BOT_TOKEN"
_DB_URI_VAR_NAME = "DB_URI"

_START_MESSAGE = (
    "Hi there! I'm a bot designed to assist you in rephrasing your text into polished English. "
    "Please type whatever you want to be rewritten, and I'll rework it into proper English for you."
)


async def start_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_START_MESSAGE)


async def get_model_command(
    update: Update,
    _: ContextTypes.DEFAULT_TYPE,
    db_client: DBClient,
) -> None:
    """Get the current model being used by the user."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    account = db_client.get_or_create_account(user_id=user_id, username=username)
    await update.message.reply_text(
        f"You are currently using {account.model.value} provided by {account.provider.value}."
    )


async def rewrite(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_client: DBClient,
) -> None:
    # Handle the message
    input_message = None
    if update.message is not None:
        input_message = update.message.text
    elif update.edited_message is not None:
        input_message = update.edited_message.text
    assert input_message is not None, "No message to rewrite."
    # Handle the user
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    account = db_client.get_or_create_account(user_id=user_id, username=username)
    # Check if the user has run out of tokens.
    # If the user is a friend, they have an unlimited token balance. ;)
    if not account.is_friend and account.tokens_balance <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You have run out of tokens. 🥲\n Please contact the bot owner to get more.",
        )
        return
    # Rewrite the message. Do not touch the user's token balance if they are a friend.
    llm_client = LLMClient(provider=account.provider, model=account.model)
    rewritten_text, num_tokens = llm_client.rewrite(input_message)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=rewritten_text,
    )
    if not account.is_friend:
        db_client.decrease_token_balance(account=account, num_tokens=num_tokens)


if __name__ == "__main__":
    db_client = DBClient(db_url=os.getenv(_DB_URI_VAR_NAME))

    app = ApplicationBuilder().token(os.getenv(_TELEGRAM_BOT_TOKEN_VAR_NAME)).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(
        CommandHandler("model", partial(get_model_command, db_client=db_client))
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND),
            partial(rewrite, db_client=db_client),
        )
    )

    app.run_polling()
