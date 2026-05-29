"""
Kimi (Moonshot AI) provider.
Kimi's API is OpenAI-compatible, so we reuse the openai SDK
pointed at Moonshot's base URL: https://api.moonshot.cn/v1

Available models:
  moonshot-v1-8k    —  8k context
  moonshot-v1-32k   —  32k context
  moonshot-v1-128k  —  128k context
"""

from typing import AsyncIterator
from openai import AsyncOpenAI
from .base import BaseProvider

KIMI_BASE_URL = "https://api.moonshot.cn/v1"


class KimiProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=KIMI_BASE_URL
        )

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
