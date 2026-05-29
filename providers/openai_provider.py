"""
OpenAI provider — uses the openai Python SDK.
Supports: /api/chat, /api/generate, /api/embeddings

Also used as the base for any OpenAI-compatible API (e.g. Kimi, Together, etc.)
by passing a custom base_url.
"""

from typing import AsyncIterator
from openai import AsyncOpenAI
from .base import BaseProvider


class OpenAIProvider(BaseProvider):

    def __init__(self, api_key: str, model: str, base_url: str = None):
        super().__init__(api_key, model)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs)

    def _build_params(self, messages: list[dict], options: dict) -> dict:
        params = {"model": self.model, "messages": messages}
        if options:
            if "temperature" in options:
                params["temperature"] = options["temperature"]
            if "top_p" in options:
                params["top_p"] = options["top_p"]
            if "num_predict" in options:        # Ollama name → OpenAI name
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
        async with self.client.chat.completions.stream(**params) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta

    async def embed(self, text: str) -> list[float]:
        # Use an embedding model if the current model looks like a chat model
        embed_model = self.model if "embedding" in self.model else "text-embedding-3-small"
        response = await self.client.embeddings.create(model=embed_model, input=text)
        return response.data[0].embedding
