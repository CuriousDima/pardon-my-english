from enum import Enum, auto
from typing import Callable, Union
import os

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.base import BasePromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.callbacks.tracers import ConsoleCallbackHandler
from langchain.prompts import HumanMessagePromptTemplate
from langchain.schema import StrOutputParser


_GROQ_API_KEY_VAR_NAME = "GROQ_API_KEY"
_OPENAI_API_KEY = "OPENAI_API_KEY"

_SYSTEM_MESSAGE = (
    "You are a professional editor. Your task is to rewrite texts.\n"
    "I will provide you texts and your task is to rewrite them in standard, casual American English, "
    "and fix any style, spelling, grammar, or punctuation errors. It has to be clear and concise, "
    "and must preserve the original meaning.\n"
    "Provide transitional phrases when needed. Provide me with rewritten text without any prefix "
    "or suffix. The text to rewrite is in quotation marks."
)

_REWRITE_PROMPT: BasePromptTemplate = ChatPromptTemplate.from_messages(
    [
        SystemMessage(_SYSTEM_MESSAGE),
        HumanMessagePromptTemplate.from_template("{text}"),
    ]
)


class Provider(Enum):
    OPENAI = auto()
    GROQ = auto()


class Model(Enum):
    GPT3 = "gpt-3.5-turbo"
    GPT4 = "gpt-4.0-turbo"
    MIXTRAL = "mixtral-8x7b-32768"
    GEMMA = "gemma-7b-it"


# OpenAI can be used as a provider with the following models: GPT3, GPT4.
# GROQ can be used as a provider with the following models: MIXTRAL, GEMMA.
def is_valid_provider_model_combination(provider: Provider, model: Model) -> bool:
    if provider == Provider.OPENAI:
        return model in [Model.GPT3, Model.GPT4]
    elif provider == Provider.GROQ:
        return model in [Model.MIXTRAL, Model.GEMMA]


def _create_openai_chat(
    model: Model, temperature: float
) -> Callable[[Model, str, float], ChatOpenAI]:
    api_key = os.getenv(_OPENAI_API_KEY)
    return ChatOpenAI(model=model.value, api_key=api_key, temperature=temperature)


def _create_groq_chat(
    model: Model, temperature: float
) -> Callable[[Model, str, float], ChatGroq]:
    api_key = os.getenv(_GROQ_API_KEY_VAR_NAME)
    return ChatGroq(
        model_name=model.value, groq_api_key=api_key, temperature=temperature
    )


def get_chat(
    provider: Provider, model: Model
) -> Callable[[Model, str, float], Union[ChatOpenAI, ChatGroq]]:
    if not is_valid_provider_model_combination(provider, model):
        raise ValueError("Invalid provider-model combination: {provider}-{model}")
    if provider == Provider.OPENAI:
        return _create_openai_chat
    elif provider == Provider.GROQ:
        return _create_groq_chat


class LLMClient:
    def __init__(
        self, provider: Provider, model: Model, temperature: float = 0.5
    ) -> None:
        self.chat = get_chat(provider, model)(model, temperature)

    def rewrite(self, text: str) -> str:
        output_parser = StrOutputParser()
        chain = _REWRITE_PROMPT | self.chat | output_parser
        return chain.invoke(
            {"text": text},
            config={"callbacks": [ConsoleCallbackHandler()]},
        )
