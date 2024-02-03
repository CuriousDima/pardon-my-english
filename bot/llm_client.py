import os

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

API_KEY_ENV_VAR_NAME = "OPENAI_API_KEY"

# Current version expects .env file to be in the same directory as the bot.
# The .env file contains the following:
#     - OPENAI_API_KEY - OpenAI API key
# However, this implementation does not allow for multiple users to use
# the bot with their own API keys. This is a known issue.
# We will address this in a future version.
# TODO: Add support for multiple users with their own API keys.
load_dotenv()

template = ChatPromptTemplate.from_messages([
    ("system", "You are a professional proofreader, you are here to help me with rewriting texts. "
     "I will provide you texts and I would like you to review and rewerite them, and fix "
     "any style, spelling, grammar, or punctuation errors. Once you have finished reviewing, "
     "provide me with corrected text."),
    ("human", "The text to proofread, rewrite, and fix is: {text}"),
])


class LLMClient:
    def __init__(self) -> None:
        api_key: str = os.getenv(API_KEY_ENV_VAR_NAME)
        if api_key is None:
            raise ValueError(
                f"Environment variable {API_KEY_ENV_VAR_NAME} is not set.")
        self._model: BaseChatModel = ChatOpenAI(openai_api_key=api_key)

    def proofread_and_rewrite(self, text: str) -> str:
        prompt = template.format_prompt(text=text).to_messages()
        chain = self._model.invoke(prompt)
        return chain.content


if __name__ == "__main__":
    client = LLMClient()
    text = ("I really appreciate the last lesson from yeaterday. "
            "I would like to learn more from you during this semester.")
    print(client.proofread_and_rewrite(text))
