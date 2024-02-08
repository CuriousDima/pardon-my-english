import os

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers.base import BaseOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.base import BasePromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_openai import ChatOpenAI
from langchain.prompts import HumanMessagePromptTemplate
from langchain.schema import StrOutputParser

API_KEY_ENV_VAR_NAME: str = "OPENAI_API_KEY"
TEXT_FIELD_NAME: str = "text"

SYSTEM_MESSAGE: str = (
    "You are a professional proofreader, you are here to help me with rewriting texts. "
    "I will provide you texts and I would like you to review and rewrite them in proper English, "
    "and fix any style, spelling, grammar, or punctuation errors. Once you have finished reviewing, "
    "provide me with corrected text without any prefix or suffix."
)
prompt: BasePromptTemplate = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=SYSTEM_MESSAGE),
        HumanMessagePromptTemplate.from_template(
            # Do not rename {text} field, it is used by the LLMClient.rewrite method.
            "The text to proofread, rewrite, and fix is: {text}"
        ),
    ]
)


class LLMClient:
    """LLMClient is a client class for interacting with the OpenAI API."""

    def __init__(self, api_key: str) -> None:
        """Initializes the LLMClient object."""
        self.llm: BaseChatModel = ChatOpenAI(openai_api_key=api_key)

    def rewrite(self, text: str) -> str:
        """Rewrites the given text."""
        output_parser: BaseOutputParser = StrOutputParser()
        chain: RunnableSequence = prompt | self.llm | output_parser
        return chain.invoke({TEXT_FIELD_NAME: text})


if __name__ == "__main__":
    # load_dotenv() is in use only for local development and testing.
    load_dotenv()

    api_key: str = os.getenv(API_KEY_ENV_VAR_NAME)
    if api_key is None:
        raise ValueError(f"Environment variable {API_KEY_ENV_VAR_NAME} is not set.")

    client = LLMClient(api_key=api_key)
    text: str = (
        "Snow weather in New York make me very surprise, so much white and cold!"
    )
    print(client.rewrite(text))
