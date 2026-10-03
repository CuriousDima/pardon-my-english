import os
from enum import Enum

from openai import AsyncOpenAI

OPENROUTER_API_KEY_VAR_NAMES = ("OPENROUTER_API_KEY", "OPENROUTER_KEY")
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OLLAMA_API_BASE_VAR_NAME = "OLLAMA_API_BASE"
DEFAULT_OLLAMA_API_BASE = "http://192.168.86.46:8000"

# Optional OpenRouter attribution headers: https://openrouter.ai/docs/api-reference/overview#headers
_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://t.me/PardonMyEnglishBot",
    "X-Title": "Pardon My English",
}

_SYSTEM_MESSAGE = (
    "You are a professional editor. Your task is to rewrite texts.\n"
    "I will provide you texts and your task is to rewrite them in standard, casual American English, "
    "and fix any style, spelling, grammar, or punctuation errors. It has to be clear and concise, "
    "and must preserve the original meaning.\n"
    "Provide transitional phrases when needed. Provide me with rewritten text without any prefix "
    "or suffix. The text to rewrite is in quotation marks."
)


class Provider(Enum):
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class Model(Enum):
    GPT54 = "openai/gpt-5.4"
    QWEN25_CODER_1_5B = "qwen2.5-coder:1.5b"


VALID_PROVIDER_MODEL_COMBINATIONS = frozenset(
    {
        (Provider.OPENROUTER, Model.GPT54),
        (Provider.OLLAMA, Model.QWEN25_CODER_1_5B),
    }
)


def is_valid_provider_model_combination(provider: Provider, model: Model) -> bool:
    return (provider, model) in VALID_PROVIDER_MODEL_COMBINATIONS


def _get_openrouter_api_key() -> str:
    for var_name in OPENROUTER_API_KEY_VAR_NAMES:
        if api_key := os.getenv(var_name):
            return api_key
    raise ValueError(f"None of {', '.join(OPENROUTER_API_KEY_VAR_NAMES)} is set.")


def _create_client(provider: Provider) -> AsyncOpenAI:
    if provider == Provider.OPENROUTER:
        return AsyncOpenAI(
            base_url=OPENROUTER_API_BASE,
            api_key=_get_openrouter_api_key(),
            default_headers=_OPENROUTER_HEADERS,
        )
    if provider == Provider.OLLAMA:
        # Ollama exposes an OpenAI-compatible API under /v1 and ignores the API key.
        api_base = os.getenv(OLLAMA_API_BASE_VAR_NAME, DEFAULT_OLLAMA_API_BASE)
        return AsyncOpenAI(base_url=f"{api_base.rstrip('/')}/v1", api_key="ollama")
    raise ValueError(f"Unsupported provider: {provider}")


class LLMClient:
    """Rewrites text using one of the supported OpenAI-compatible backends.

    Clients are created lazily and reused across calls, one per provider.
    """

    def __init__(self, temperature: float = 0.35) -> None:
        self.temperature = temperature
        self._clients: dict[Provider, AsyncOpenAI] = {}

    def _get_client(self, provider: Provider) -> AsyncOpenAI:
        if provider not in self._clients:
            self._clients[provider] = _create_client(provider)
        return self._clients[provider]

    async def rewrite(
        self, text: str, provider: Provider, model: Model
    ) -> tuple[str, int]:
        """Return the rewritten text and the number of tokens spent."""
        if not is_valid_provider_model_combination(provider, model):
            raise ValueError(f"Invalid provider-model combination: {provider}-{model}")
        response = await self._get_client(provider).chat.completions.create(
            model=model.value,
            messages=[
                {"role": "system", "content": _SYSTEM_MESSAGE},
                {"role": "user", "content": text},
            ],
            temperature=self.temperature,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError(f"Empty response from {provider.value}/{model.value}.")
        total_tokens = response.usage.total_tokens if response.usage else 0
        return content.strip(), total_tokens
