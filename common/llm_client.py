from enum import Enum
import os
from typing import Any, Tuple

from litellm import completion


OPENAI_API_KEY = "OPENAI_API_KEY"
OLLAMA_API_BASE_VAR_NAME = "OLLAMA_API_BASE"
DEFAULT_OLLAMA_API_BASE = "http://192.168.86.46:8000"

_SYSTEM_MESSAGE = (
    "You are a professional editor. Your task is to rewrite texts.\n"
    "I will provide you texts and your task is to rewrite them in standard, casual American English, "
    "and fix any style, spelling, grammar, or punctuation errors. It has to be clear and concise, "
    "and must preserve the original meaning.\n"
    "Provide transitional phrases when needed. Provide me with rewritten text without any prefix "
    "or suffix. The text to rewrite is in quotation marks."
)


class Provider(Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"


class Model(Enum):
    GPT54 = "gpt-5.4"
    QWEN25_CODER_1_5B = "qwen2.5-coder:1.5b"


def is_valid_provider_model_combination(provider: Provider, model: Model) -> bool:
    return (provider == Provider.OPENAI and model == Model.GPT54) or (
        provider == Provider.OLLAMA and model == Model.QWEN25_CODER_1_5B
    )


def _get_total_tokens(response: Any) -> int:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get("total_tokens", 0) or 0)
    return int(getattr(usage, "total_tokens", 0) or 0)


def _get_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif hasattr(item, "text"):
                parts.append(getattr(item, "text"))
        return "".join(parts)
    raise ValueError(f"Unsupported LiteLLM response content: {type(content)!r}")


class LLMClient:
    def __init__(
        self, provider: Provider, model: Model, temperature: float = 0.35
    ) -> None:
        if not is_valid_provider_model_combination(provider, model):
            raise ValueError(f"Invalid provider-model combination: {provider}-{model}")
        self.provider = provider
        self.model = model
        self.temperature = temperature

    def _provider_kwargs(self) -> dict[str, Any]:
        if self.provider == Provider.OPENAI:
            api_key = os.getenv(OPENAI_API_KEY)
            if not api_key:
                raise ValueError("OPENAI_API_KEY is not set.")
            return {"api_key": api_key}
        if self.provider == Provider.OLLAMA:
            return {
                "api_base": os.getenv(
                    OLLAMA_API_BASE_VAR_NAME,
                    DEFAULT_OLLAMA_API_BASE,
                ).rstrip("/")
            }
        raise ValueError(f"Unsupported provider: {self.provider}")

    def rewrite(self, text: str) -> Tuple[str, int]:
        response = completion(
            model=f"{self.provider.value}/{self.model.value}",
            messages=[
                {"role": "system", "content": _SYSTEM_MESSAGE},
                {"role": "user", "content": text},
            ],
            temperature=self.temperature,
            **self._provider_kwargs(),
        )
        content = response.choices[0].message.content
        return _get_text_content(content), _get_total_tokens(response)
