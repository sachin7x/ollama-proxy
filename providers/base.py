"""
base.py — Abstract base class all providers must implement.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseProvider(ABC):

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def chat(self, messages: list[dict], stream: bool = False, options: dict = None) -> str:
        """Non-streaming chat. Returns the full assistant reply as a string."""
        ...

    @abstractmethod
    async def chat_stream(self, messages: list[dict], options: dict = None) -> AsyncIterator[str]:
        """Streaming chat. Yields text chunks as they arrive."""
        ...

    # Optional — override in providers that support embeddings
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(f"{self.__class__.__name__} does not support embeddings.")
