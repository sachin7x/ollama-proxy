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

    def _build_params(self, messages: list[dict], options: dict) -> tuple[dict, dict]:
        """Returns (params, extra_body) tuple."""
        params = {"model": self.model, "messages": messages}
        extra_body = {}
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
            # Tools pass-through (Ollama /api/chat tools or OpenAI tools)
            if "_tools" in options:
                params["tools"] = options["_tools"]
            # Format / structured output (Ollama format or OpenAI response_format)
            if "_format" in options:
                fmt = options["_format"]
                if fmt == "json":
                    params["response_format"] = {"type": "json_object"}
                elif isinstance(fmt, dict):
                    # JSON schema passed directly
                    params["response_format"] = {"type": "json_schema", "json_schema": {"name": "response", "schema": fmt}}
            if "_response_format" in options:
                params["response_format"] = options["_response_format"]
            # Non-standard params passed directly in the request body
            if "_extra_body" in options:
                extra_body = options["_extra_body"]
        return params, extra_body

    async def chat(self, messages: list[dict], stream: bool = False, options: dict = None) -> str:
        params, extra_body = self._build_params(messages, options or {})
        if extra_body:
            params["extra_body"] = extra_body
        response = await self.client.chat.completions.create(**params)
        return response.choices[0].message.content or ""

    async def chat_full(self, messages: list[dict], options: dict = None) -> dict:
        """Return full response message (content + tool_calls) for OpenAI passthrough."""
        params, extra_body = self._build_params(messages, options or {})
        if extra_body:
            params["extra_body"] = extra_body
        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]
        msg = choice.message
        result = {
            "role": msg.role or "assistant",
            "content": msg.content or "",
            "finish_reason": choice.finish_reason or "stop",
        }
        if msg.tool_calls:
            result["tool_calls"] = [tc.model_dump(exclude_none=True) for tc in msg.tool_calls]
        if response.usage:
            result["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return result

    async def chat_stream(self, messages: list[dict], options: dict = None) -> AsyncIterator[str]:
        """Stream text content only (for Ollama-format endpoints)."""
        params, extra_body = self._build_params(messages, options or {})
        params["stream"] = True
        if extra_body:
            params["extra_body"] = extra_body
        response = await self.client.chat.completions.create(**params)
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def chat_stream_raw(self, messages: list[dict], options: dict = None):
        """Stream raw chunks (content + tool_calls + finish_reason) for OpenAI passthrough.
        Yields dicts: {"content": str, "tool_calls": [...], "finish_reason": str|None}
        """
        params, extra_body = self._build_params(messages, options or {})
        params["stream"] = True
        if extra_body:
            params["extra_body"] = extra_body
        response = await self.client.chat.completions.create(**params)
        async for chunk in response:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            out = {}
            if delta.content:
                out["content"] = delta.content
            if delta.tool_calls:
                # Convert pydantic models to plain dicts for JSON serialization
                out["tool_calls"] = [tc.model_dump(exclude_none=True) for tc in delta.tool_calls]
            if delta.role:
                out["role"] = delta.role
            if choice.finish_reason:
                out["finish_reason"] = choice.finish_reason
            if out:
                yield out

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding
