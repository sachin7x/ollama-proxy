"""
Azure OpenAI provider — uses the openai SDK's AzureOpenAI client.
Supports: /api/chat, /api/generate, /api/embeddings

Azure-specific concepts mapped here:
  - "model" in the Ollama request = the Azure DEPLOYMENT NAME
    (the name you gave when you deployed the model in Azure AI Studio)
  - Requires AZURE_OPENAI_ENDPOINT  e.g. https://my-resource.openai.azure.com/
  - Requires AZURE_OPENAI_API_KEY
  - Requires AZURE_OPENAI_API_VERSION  e.g. 2024-08-01-preview

Example Ollama model strings:
  azure/my-gpt4o-deployment
  azure/my-gpt35-deployment
  azure/my-embedding-deployment

Multiple Azure deployments across different resources / API versions:
  Add extra entries to AZURE_DEPLOYMENTS in config.py (see example there).
"""

from typing import AsyncIterator
from openai import AsyncAzureOpenAI
from .base import BaseProvider


class AzureProvider(BaseProvider):

    def __init__(
        self,
        api_key: str,
        model: str,           # deployment name
        endpoint: str,
        api_version: str,
    ):
        super().__init__(api_key, model)
        self.client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )

    def _build_params(self, messages: list[dict], options: dict) -> dict:
        # In Azure, `model` = deployment name
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
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
