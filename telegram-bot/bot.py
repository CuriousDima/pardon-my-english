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

from llm_client import LLMClient, Model, Provider


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
load_dotenv()

# Environment variables names
_TELEGRAM_BOT_TOKEN_VAR_NAME = "TELEGRAM_BOT_TOKEN"

_START_MESSAGE = (
    "Hi there! I'm a bot designed to assist you in rephrasing your text into polished English. "
    "Please type whatever you want to be rewritten, and I'll rework it into proper English for you."
)


async def start_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info(f"User {update.effective_user.id} started the bot.")
    await update.message.reply_text(_START_MESSAGE)


async def rewrite(
    update: Update, context: ContextTypes.DEFAULT_TYPE, llm_client: LLMClient
) -> None:
    input_message = None
    if update.message is not None:
        input_message = update.message.text
    elif update.edited_message is not None:
        input_message = update.edited_message.text
    assert input_message is not None, "No message to rewrite."
    rewritten_text = llm_client.rewrite(input_message)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=rewritten_text,
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv(_TELEGRAM_BOT_TOKEN_VAR_NAME)).build()

    app.add_handler(CommandHandler("start", start_command))

    llm_client = LLMClient(provider=Provider.GROQ, model=Model.GEMMA)
    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND), partial(rewrite, llm_client=llm_client)
        )
    )

    app.run_polling()
