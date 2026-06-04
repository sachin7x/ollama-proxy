# Adding a new provider

There are two cases:

1. **OpenAI-compatible** — provider speaks the OpenAI chat completions
   format. **No code changes needed**, just configuration.
2. **Custom wire format** — provider has a different API shape (e.g.
   Cohere, Vertex AI's native API). Requires writing a new provider class.

## Case 1 — OpenAI-compatible

You have two ways to add it.

### Option A — environment variables (auto-discovered)

The proxy scans the environment on startup for any
`PROVIDERS_<NAME>_API_KEY` / `PROVIDERS_<NAME>_BASE_URL` pair and registers
them automatically:

```bash
export PROVIDERS_VLLM_API_KEY=EMPTY
export PROVIDERS_VLLM_BASE_URL=http://localhost:8000/v1
ollama-proxy
```

Use `vllm/<model-id>` in clients. The lowercased name (`vllm`) becomes the
routing prefix.

### Option B — YAML config file

```yaml
# ollama-proxy.yaml
providers:
  myprovider:
    api_key: ${MYPROVIDER_API_KEY}     # ${...} env-var expansion
    base_url: https://api.myprovider.com/v1
```

```bash
ollama-proxy --config ollama-proxy.yaml
```

### Built-in known providers

The proxy ships with these prefixes pre-registered, so all you need to set
is the env var with the API key:

```
openai gemini xai groq mistral deepseek together perplexity kimi
```

Override the base URL or api_key in YAML if you need to.

## Case 2 — Custom wire format

For providers that don't speak OpenAI-compatible chat completions, write a
provider class.

### 1. Create a provider file

`ollama_proxy/providers/myprovider_provider.py`:

```python
from typing import AsyncIterator

from .base import BaseProvider


class MyProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        # Initialize your SDK client
        # self.client = some_sdk.AsyncClient(api_key=api_key)

    async def chat(
        self, messages: list[dict], stream: bool = False, options: dict = None
    ) -> str:
        # Translate messages + options to your provider's request format
        # Call the API and return the text content
        ...

    async def chat_stream(
        self, messages: list[dict], options: dict = None
    ) -> AsyncIterator[str]:
        # Yield text chunks as they arrive
        ...

    # Optional — for tool calls and structured streaming
    async def chat_full(self, messages: list[dict], options: dict = None) -> dict:
        # Return {"role": ..., "content": ..., "tool_calls": [...], "finish_reason": ..., "usage": {...}}
        ...

    # Optional — for embeddings
    async def embed(self, text: str) -> list[float]:
        ...
```

### 2. Wire it into routing

Add a branch in `ollama_proxy/server.py::get_provider()`:

```python
if prefix == "myprovider":
    return MyProvider(api_key=API_KEYS["myprovider"], model=model_id)
```

And add the API key to `API_KEYS` in `ollama_proxy/config.py`:

```python
API_KEYS = {
    "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
    "myprovider": os.getenv("MYPROVIDER_API_KEY", ""),
}
```

### 3. (Optional) Add models to the registry

```python
PROVIDER_REGISTRY = [
    # ...
    "myprovider/some-model",
    "myprovider/another-model",
]
```

This is purely for `/api/tags` discovery — direct API calls work without
this step.

### 4. Test it

```bash
ollama-proxy test myprovider/some-model --prompt "Say hi"
```

## Method-level capabilities

| Method | Purpose | Required? |
|--------|---------|-----------|
| `chat()` | Non-streaming text completion | yes |
| `chat_stream()` | Streaming text completion (yields text chunks) | yes |
| `chat_full()` | Returns structured response with `tool_calls`, `finish_reason`, `usage` | optional — needed for tool calls in non-streaming `/v1/chat/completions` |
| `chat_stream_raw()` | Streams structured chunks (`content`, `tool_calls`, `finish_reason`) | optional — needed for tool calls in streaming `/v1/chat/completions` |
| `embed()` | Generate an embedding vector | optional — needed for `/api/embed` |

If `chat_full` and `chat_stream_raw` are not implemented, the proxy falls
back to text-only mode (no tool call support on the OpenAI-compat endpoint).
