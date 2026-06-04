"""
AWS Bedrock provider — uses boto3 Converse API.
Supports: /api/chat, /api/generate

Bedrock uses the Converse API which provides a unified interface across all
Bedrock-hosted models (Claude, Nova, Llama, Mistral, etc.)

Auth: Uses standard AWS credential chain (env vars, ~/.aws/credentials, IAM role).
  - AWS_REGION or AWS_DEFAULT_REGION
  - AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (+ optional AWS_SESSION_TOKEN)
  - Or any other boto3-supported credential source (instance profile, SSO, etc.)

Model naming:
  bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0
  bedrock/us.amazon.nova-pro-v1:0
  bedrock/us.meta.llama3-1-70b-instruct-v1:0
"""

from typing import AsyncIterator
import asyncio
from .base import BaseProvider


class BedrockProvider(BaseProvider):

    def __init__(self, model: str, region: str, profile: str | None = None):
        # Bedrock doesn't use an api_key, pass empty string to satisfy base class
        super().__init__(api_key="", model=model)
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as e:
            raise ImportError(
                "Bedrock provider requires the 'boto3' package. "
                "Install with: pip install ollama-proxy[bedrock]"
            ) from e
        session_kwargs = {}
        if profile:
            session_kwargs["profile_name"] = profile
        if region:
            session_kwargs["region_name"] = region
        session = boto3.Session(**session_kwargs)
        self.client = session.client(
            "bedrock-runtime",
            config=BotoConfig(
                read_timeout=300,
                retries={"max_attempts": 2},
            ),
        )

    def _split_messages(self, messages: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Separate system messages from chat messages and convert to Bedrock format.
        Bedrock Converse expects:
          system: [{"text": "..."}]
          messages: [{"role": "user"|"assistant", "content": [{"text": "..."}]}]
        """
        system_parts = []
        chat_messages = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_parts.append({"text": content})
            else:
                chat_messages.append({
                    "role": role,
                    "content": [{"text": content}],
                })

        return system_parts, chat_messages

    def _build_inference_config(self, options: dict) -> dict:
        """Map Ollama options to Bedrock inferenceConfig."""
        cfg = {}
        if not options:
            return cfg
        if "temperature" in options:
            cfg["temperature"] = float(options["temperature"])
        if "top_p" in options:
            cfg["topP"] = float(options["top_p"])
        if "num_predict" in options:
            cfg["maxTokens"] = int(options["num_predict"])
        if "max_tokens" in options:
            cfg["maxTokens"] = int(options["max_tokens"])
        if "stop" in options:
            stops = options["stop"]
            cfg["stopSequences"] = stops if isinstance(stops, list) else [stops]
        return cfg

    async def chat(self, messages: list[dict], stream: bool = False, options: dict = None) -> str:
        system_parts, chat_messages = self._split_messages(messages)
        inference_config = self._build_inference_config(options or {})

        params = {
            "modelId": self.model,
            "messages": chat_messages,
        }
        if system_parts:
            params["system"] = system_parts
        if inference_config:
            params["inferenceConfig"] = inference_config

        # boto3 is synchronous — run in thread pool
        response = await asyncio.to_thread(self.client.converse, **params)

        # Extract text from response
        output = response["output"]["message"]["content"]
        return "".join(block.get("text", "") for block in output)

    async def chat_stream(self, messages: list[dict], options: dict = None) -> AsyncIterator[str]:
        system_parts, chat_messages = self._split_messages(messages)
        inference_config = self._build_inference_config(options or {})

        params = {
            "modelId": self.model,
            "messages": chat_messages,
        }
        if system_parts:
            params["system"] = system_parts
        if inference_config:
            params["inferenceConfig"] = inference_config

        # converse_stream is synchronous — run in thread and yield chunks
        response = await asyncio.to_thread(self.client.converse_stream, **params)
        event_stream = response["stream"]

        # Iterate the EventStream in a thread to avoid blocking
        for event in event_stream:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                text = delta.get("text", "")
                if text:
                    yield text
