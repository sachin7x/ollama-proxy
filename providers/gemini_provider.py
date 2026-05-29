"""
Google Gemini provider — uses google-generativeai SDK.
Supports: /api/chat, /api/generate

Role mapping:
  Ollama "user"      → Gemini "user"
  Ollama "assistant" → Gemini "model"
  Ollama "system"    → Gemini system_instruction (constructor arg)
"""

from typing import AsyncIterator
import google.generativeai as genai
from .base import BaseProvider


class GeminiProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)

    def _split_messages(self, messages: list[dict]) -> tuple[str | None, list[dict]]:
        """
        Extract system prompt (Gemini needs it separately) and convert
        the remaining messages to Gemini's {role, parts} format.
        """
        system_text = None
        history = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_text = content
            elif role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})

        return system_text, history

    def _gen_config(self, options: dict) -> dict:
        cfg = {}
        if not options:
            return cfg
        if "temperature" in options:
            cfg["temperature"] = options["temperature"]
        if "top_p" in options:
            cfg["top_p"] = options["top_p"]
        if "top_k" in options:
            cfg["top_k"] = options["top_k"]
        if "num_predict" in options:
            cfg["max_output_tokens"] = options["num_predict"]
        if "stop" in options:
            stops = options["stop"]
            cfg["stop_sequences"] = stops if isinstance(stops, list) else [stops]
        return cfg

    def _build_model(self, system_text: str | None):
        return genai.GenerativeModel(
            self.model,
            system_instruction=system_text
        ) if system_text else genai.GenerativeModel(self.model)

    async def chat(self, messages: list[dict], stream: bool = False, options: dict = None) -> str:
        system_text, history = self._split_messages(messages)
        model = self._build_model(system_text)
        *prior, last = history
        session = model.start_chat(history=prior)
        cfg = self._gen_config(options or {})
        response = await session.send_message_async(
            last["parts"][0],
            generation_config=cfg if cfg else None
        )
        return response.text

    async def chat_stream(self, messages: list[dict], options: dict = None) -> AsyncIterator[str]:
        system_text, history = self._split_messages(messages)
        model = self._build_model(system_text)
        *prior, last = history
        session = model.start_chat(history=prior)
        cfg = self._gen_config(options or {})
        response = await session.send_message_async(
            last["parts"][0],
            generation_config=cfg if cfg else None,
            stream=True
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text
