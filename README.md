# Pardon My English

**tl;dr: The bot that uses preset prompts to help users communicate like native English speakers.**

It is freely available. Go ahead and give it a try: https://t.me/PardonMyEnglishBot.  

Pardon My English is designed to assist non-native English speakers by transforming semantically incorrect or awkwardly phrased English text into grammatically accurate and fluent English. Users simply input their original text, and the bot efficiently processes and returns a polished version, enhancing clarity and coherence. Ideal for learners of English, professionals, and anyone looking to improve their written communication.

# Changelog

- \[2026-03-15\] Migrated the project to `uv` and Python 3.11, replaced LangChain with LiteLLM, reset all existing users to OpenAI `gpt-5.4`, and added Ollama support for `qwen2.5-coder:1.5b`.
- \[2024-11-05\] GPT-4o is now the default and included in the config. All current users have been migrated to 4o too.
- \[2024-09-15\] Llama 3.1 via Perplexity API is now a default mode for everyone!
- \[2024-08-05\] We've updated Llama version to Llama 3.1 via Perplexity API.
- \[2024-05-28\] We've added support for the Perplexity API, which now integrates with Llama3-70b-instruct. When selected, it adheres more closely to the initial instructions.
- \[2024-04-24\] We've transitioned to using Llama3-70B for all existing and new users, and have seen significant improvements in quality without any degradation in inference speed, thanks to the capabilities of [Groq](https://groq.com/).

# Setup

```shell
uv sync
```

Set `DB_URI` to either a full SQLAlchemy URL or a SQLite file path such as `./pardon-my-english-accounts.db`.

The bot supports these backends:

- OpenAI: `gpt-5.4`
- Ollama

`gpt-5.4` is the default for all new accounts.

For OpenAI, set `OPENAI_API_KEY`.

To run the Telegram bot locally:

```shell
uv run python telegram-bot/bot.py
```

Once the bot is running:

- `/model` shows the backend currently selected for your account
