"""
Generic OpenAI-compatible provider.

Any LLM provider that exposes an OpenAI-compatible REST API can be handled
here by simply passing a base_url. No extra SDK installs needed.

Providers using this adapter:
  xAI / Grok      https://api.x.ai/v1
  Groq            https://api.groq.com/openai/v1
  Mistral AI      https://api.mistral.ai/v1
  DeepSeek        https://api.deepseek.com
  Together AI     https://api.together.xyz/v1
  Perplexity      https://api.perplexity.ai

Usage (internal - called from main.py get_provider()):
  OpenAICompatProvider(api_key="sk-...", model="grok-2", base_url="https://api.x.ai/v1")
"""

from typing import AsyncIterator
from openai import AsyncOpenAI
from .base import BaseProvider


class OpenAICompatProvider(BaseProvider):

    def __init__(self, api_key: str, model: str, base_url: str):
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _build_params(self, messages: list[dict], options: dict) -> dict:
        params = {"model": self.model, "messages": messages}
        if options:
            if "temperature" in options:
                params["temperature"] = options["temperature"]
            if "top_p" in options:
                params["top_p"] = options["top_p"]
            if "num_predict" in options:
                params["max_tokens"] = options["num_predict"]
            if "max_tokens" in options:
                params["max_tokens"] = options["max_tokens"]
            if "stop" in options:
                params["stop"] = options["stop"]
        return params

    async def chat(self, messages: list[dict], stream: bool = False, options: dict = None) -> str:
        params = self._build_params(messages, options or {})
        response = await self.client.chat.completions.create(**params)
        return response.choices[0].message.content or ""

    async def chat_stream(self, messages: list[dict], options: dict = None) -> AsyncIterator[str]:
        params = self._build_params(messages, options or {})
        params["stream"] = True
        response = await self.client.chat.completions.create(**params)
        async for chunk in response:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding
