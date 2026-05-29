"""
Anthropic / Claude provider — uses the anthropic Python SDK.
Supports: /api/chat, /api/generate

Anthropic quirks handled here:
  - System prompt must be passed as a top-level 'system' param, not inside messages[]
  - Requires max_tokens (we default to 4096)
  - Role must be 'user' or 'assistant' only (no 'system' in messages)
"""

from typing import AsyncIterator
import anthropic
from .base import BaseProvider


class AnthropicProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def _split_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """
        Pull out system messages (Anthropic requires them separately)
        and return (system_string, chat_messages).
        """
        system_parts = []
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})
        return "\n\n".join(system_parts), chat_messages

    def _build_params(self, messages: list[dict], options: dict) -> dict:
        system_text, chat_messages = self._split_messages(messages)
        params = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": 4096,
        }
        if system_text:
            params["system"] = system_text
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
                stops = options["stop"]
                params["stop_sequences"] = stops if isinstance(stops, list) else [stops]
        return params

    async def chat(self, messages: list[dict], stream: bool = False, options: dict = None) -> str:
        params = self._build_params(messages, options or {})
        response = await self.client.messages.create(**params)
        return response.content[0].text

    async def chat_stream(self, messages: list[dict], options: dict = None) -> AsyncIterator[str]:
        params = self._build_params(messages, options or {})
        async with self.client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text
