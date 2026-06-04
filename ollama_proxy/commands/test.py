"""`ollama-proxy test <model>` — send a one-off chat request and print the response."""

import asyncio

from ..server import get_provider


def run(model: str, prompt: str) -> int:
    try:
        provider = get_provider(model)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    print(f"Model:  {model}")
    print(f"Prompt: {prompt}")
    print("-" * 60)

    async def _go() -> str:
        return await provider.chat(
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )

    try:
        reply = asyncio.run(_go())
    except Exception as e:
        print(f"Failed: {type(e).__name__}: {e}")
        return 2

    print(reply)
    return 0
