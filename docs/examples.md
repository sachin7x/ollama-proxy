# Client examples

The proxy speaks both the Ollama and OpenAI wire formats. Here's how to
point the most common clients at it.

## ollama Python SDK

```python
import ollama

client = ollama.Client(host="http://localhost:11434")
resp = client.chat(
    model="openai/gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(resp["message"]["content"])

# Streaming
for chunk in client.chat(
    model="anthropic/claude-sonnet-4-5",
    messages=[{"role": "user", "content": "Tell me a joke"}],
    stream=True,
):
    print(chunk["message"]["content"], end="", flush=True)
```

## OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="dummy",  # required by the SDK but ignored by the proxy
)
resp = client.chat.completions.create(
    model="kimi/kimi-k2.6",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(resp.choices[0].message.content)
```

## LangChain

```python
from langchain_community.llms import Ollama

llm = Ollama(
    base_url="http://localhost:11434",
    model="groq/llama-3.3-70b-versatile",
)
print(llm.invoke("Explain transformers in one paragraph."))
```

## LlamaIndex

```python
from llama_index.llms.ollama import Ollama

llm = Ollama(
    base_url="http://localhost:11434",
    model="gemini/gemini-2.5-flash",
)
print(llm.complete("What is RAG?"))
```

## GitHub Copilot

In VS Code, point Copilot at the proxy as an Ollama provider:

1. Open VS Code settings.
2. Search for the GitHub Copilot Ollama configuration (location varies by
   Copilot version).
3. Set the Ollama base URL to `http://localhost:11434`.
4. Enter any registered model name as `<prefix>/<model-id>` — e.g.
   `gemini/gemini-2.5-pro` or `openai/gpt-4o-mini`.

!!! tip "Tool-calling models work best"
    Copilot drives an agentic flow that requires `tool_calls`. Models that
    reliably emit OpenAI-format tool calls work well: GPT-4o, Claude
    Sonnet 4+, Gemini 2.5+. Some Kimi variants emit text descriptions
    instead of structured tool calls.

## Continue

Edit `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "GPT-4o via proxy",
      "provider": "ollama",
      "model": "openai/gpt-4o",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "Gemini 2.5 Flash via proxy",
      "provider": "ollama",
      "model": "gemini/gemini-2.5-flash",
      "apiBase": "http://localhost:11434"
    }
  ]
}
```

## Cursor

Cursor uses the OpenAI protocol. Set:

- API base URL: `http://localhost:11434/v1`
- API key: anything (the proxy holds the real keys)
- Model: `<prefix>/<model-id>`

## Open WebUI

Settings → Connections → Ollama URL: `http://localhost:11434`. All
registered models appear in the model dropdown.

## curl

```bash
# Ollama format
curl http://localhost:11434/api/chat -d '{
  "model": "openai/gpt-4o-mini",
  "messages": [{"role": "user", "content": "Hi"}]
}'

# OpenAI format
curl http://localhost:11434/v1/chat/completions -d '{
  "model": "gemini/gemini-2.5-flash",
  "messages": [{"role": "user", "content": "Hi"}]
}'
```
