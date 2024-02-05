import os

from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers.base import BaseOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.base import BasePromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_openai import ChatOpenAI
from langchain.prompts import HumanMessagePromptTemplate
from langserve import add_routes
import uvicorn

API_KEY_ENV_VAR_NAME: str = "OPENAI_API_KEY"

SYSTEM_MESSAGE: str = (
    "You are a professional proofreader, you are here to help me with rewriting texts. "
    "I will provide you texts and I would like you to review and rewerite them, and fix "
    "any style, spelling, grammar, or punctuation errors. Once you have finished reviewing, "
    "provide me with corrected text."
)
prompt: BasePromptTemplate = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=SYSTEM_MESSAGE),
        HumanMessagePromptTemplate.from_template(
            "The text to proofread, rewrite, and fix is: {text}"
        ),
    ]
)


class LLMClient:
    """LLMClient is a client class for interacting with the OpenAI API."""

    def __init__(self, api_key: str) -> None:
        """Initializes the LLMClient object."""
        self._llm: BaseChatModel = ChatOpenAI(openai_api_key=api_key)


if __name__ == "__main__":
    # If you want to run this script, you need to set the OPENAI_API_KEY environment variable.
    # Create .env file in the same directory as this script and add the following line:
    # OPENAI_API_KEY=your-api-key
    load_dotenv()
    api_key: str = os.getenv(API_KEY_ENV_VAR_NAME)
    if api_key is None:
        raise ValueError(f"Environment variable {API_KEY_ENV_VAR_NAME} is not set.")

    client = LLMClient(api_key=api_key)
    app = FastAPI(
        title="Proofreading and Rewriting API",
        version="1.0",
        description="A simple API for proofreading and rewriting texts.",
    )
    add_routes(
        app,
        prompt | client._llm,
        path="/rewrite",
    )
    uvicorn.run(app, port=18029)
