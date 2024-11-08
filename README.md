# Pardon My English

**tl;dr: The bot that uses preset prompts to help users communicate like native English speakers.**

It is freely available. Go ahead and give it a try: https://t.me/PardonMyEnglishBot.  
Web UI: https://pardonmyenglish.streamlit.app/

Pardon My English is designed to assist non-native English speakers by transforming semantically incorrect or awkwardly phrased English text into grammatically accurate and fluent English. Users simply input their original text, and the bot efficiently processes and returns a polished version, enhancing clarity and coherence. Ideal for learners of English, professionals, and anyone looking to improve their written communication.

# Changelog

- \[2024-11-05\] GPT-4o is now the default and included in the config. All current users have been migrated to 4o too.
- \[2024-09-15\] Llama 3.1 via Perplexity API is now a default mode for everyone!
- \[2024-08-05\] We've updated Llama version to Llama 3.1 via Perplexity API.
- \[2024-05-28\] We've added support for the Perplexity API, which now integrates with Llama3-70b-instruct. When selected, it adheres more closely to the initial instructions.
- \[2024-05-25\] We've added an alternative frontend. Instead of using Telegram, you can now run the app locally by using `streamlit run frontend.py` command, and interact with Pardon My English in the same way as before.
- \[2024-04-24\] We've transitioned to using Llama3-70B for all existing and new users, and have seen significant improvements in quality without any degradation in inference speed, thanks to the capabilities of [Groq](https://groq.com/).

# Web UI

If you want to run the app locally, start by creating the `secrets.toml` file:

```shell
touch ~/.streamlit/secrets.toml
```

You'll need to obtain a Groq API key, which you'll then provide in the "secrets.toml" file as a `GROQ_API_KEY`.

After specifying the API key in the secrets file, you can proceed to run the web UI locally:

```shell
streamlit run frontend.py
```
