# ollama-proxy

A lightweight server that **speaks the Ollama API protocol** but routes every
request to a cloud or self-hosted LLM backend.

Any tool that already works with Ollama — LangChain, LlamaIndex, Open WebUI,
Continue, Cursor, GitHub Copilot, the `ollama` Python SDK — connects here
with **zero code changes**.

---

## How it works

```
Your App  ---->  POST /api/chat       (Ollama format)
         ---->  POST /v1/chat/completions  (OpenAI format)
                        |
                 ollama-proxy
                        |  routes by model-name prefix
       +----------------+----------------+------- ... -------+
  openai/*        gemini/*        anthropic/*           custom/*
  OpenAI API    Gemini API      Anthropic API     your vLLM / Ray server
```

The **model name prefix** is the only routing key — no extra config needed.

The proxy speaks **two wire formats simultaneously**:
- **Ollama protocol** at `/api/*` (used by Open WebUI, ollama SDK, LangChain Ollama integration)
- **OpenAI protocol** at `/v1/*` (used by Copilot, Continue, Cursor, OpenAI SDK)

---

## Architecture

The proxy has two categories of providers:

1. **OpenAI-compatible providers** — Any provider whose API follows the OpenAI
   chat completions format. These are all handled by a single generic adapter
   (`OpenAICompatProvider`). Most providers fall here, including Gemini (via
   Google's OpenAI-compat endpoint). Adding a new one is two lines of config.

2. **Native SDK providers** — Providers with genuinely different wire formats
   that need their own implementation (Anthropic, Azure OpenAI, AWS Bedrock).

---

## OpenAI-Compatible Provider Reference

The table below lists known OpenAI-compatible providers and their base URLs.
Adding any of these (or unlisted ones) requires only a config entry — no code
changes.

> **Caveat:** Endpoints and compatibility may change over time. Always verify
> the current base URL and supported features against the provider's official
> documentation before relying on them in production.

| Prefix | Provider | Base URL | Env Variable | Docs |
|--------|----------|----------|--------------|------|
| `openai/` | OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/docs) |
| `gemini/` | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY` | [ai.google.dev](https://ai.google.dev/gemini-api/docs) |
| `xai/` | xAI / Grok | `https://api.x.ai/v1` | `XAI_API_KEY` | [console.x.ai](https://console.x.ai) |
| `groq/` | Groq | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `mistral/` | Mistral AI | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | [docs.mistral.ai](https://docs.mistral.ai) |
| `deepseek/` | DeepSeek | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | [platform.deepseek.com](https://platform.deepseek.com) |
| `together/` | Together AI | `https://api.together.xyz/v1` | `TOGETHER_API_KEY` | [docs.together.ai](https://docs.together.ai) |
| `perplexity/` | Perplexity | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | [docs.perplexity.ai](https://docs.perplexity.ai) |
| `kimi/` | Kimi / Moonshot AI | `https://api.moonshot.ai/v1` | `KIMI_API_KEY` | [platform.kimi.ai](https://platform.kimi.ai/docs) |

### Self-hosted / custom servers

Any server exposing an OpenAI-compatible REST API works the same way:

| Server | Typical Base URL |
|--------|-----------------|
| **vLLM** | `http://localhost:8000/v1` |
| **Ray Serve** (vLLM backend) | `http://localhost:8000/v1` |
| **Hugging Face TGI** | `http://localhost:8080/v1` |
| **LM Studio** | `http://localhost:1234/v1` |
| **LocalAI** | `http://localhost:8080/v1` |
| **Ollama** (real instance) | `http://localhost:11434/v1` |
| **Llamafile** | `http://localhost:8080/v1` |
| **Jan** | `http://localhost:1337/v1` |

---

## Native SDK Providers

These providers have non-OpenAI-compatible APIs and use dedicated implementations:

| Prefix | Provider | Auth | Notes |
|--------|----------|------|-------|
| `anthropic/` | Anthropic / Claude | `ANTHROPIC_API_KEY` | System prompt separate from messages, requires max_tokens |
| `azure/` | Azure OpenAI | `AZURE_OPENAI_*` vars | Deployment-based routing, needs endpoint + api_version |
| `bedrock/` | AWS Bedrock | AWS credential chain | Converse API — supports Claude, Nova, Llama, Mistral on AWS |

---

## Quick start

### 1. Install dependencies

```bash
cd ollama-proxy
pip install -r requirements.txt
# or with uv:
uv sync
```

### 2. Configure API keys

```bash
cp .env.example .env
# Fill in only the providers you need
```

Or export them in your shell — both work, the proxy reads from the environment.

### 3. Start the server

```bash
uvicorn main:app --host 0.0.0.0 --port 11434
# or with uv:
uv run uvicorn main:app --host 0.0.0.0 --port 11434
```

Port **11434** is Ollama's default — clients think they're talking to a real
Ollama instance.

---

## Adding models — three ways

### Option 1: Quick — `EXTRA_MODELS` env var (no config edits)

```bash
export EXTRA_MODELS="openai/gpt-4o-2025-08-01,gemini/gemini-3-pro,kimi/kimi-k2.7"
```

Models in this list show up in `/api/tags` immediately after restart.
Comma-separated, format `<prefix>/<model-id>`.

### Option 2: Permanent — add to `PROVIDER_REGISTRY` in `config.py`

```python
PROVIDER_REGISTRY = [
    # ... existing entries ...
    "openai/gpt-5",
    "gemini/gemini-3-flash",
]
```

### Option 3: No registration at all — just call it

The registry is **only** for `/api/tags` discovery (so models show up in
client dropdowns). You can call any `<prefix>/<model-id>` directly without
registering it, as long as the prefix is configured:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "openai/gpt-4o-2025-08-01-preview",
  "messages": [{"role": "user", "content": "Hi"}]
}'
```

The proxy will route it as long as `openai/` is a known prefix. The model
won't appear in dropdowns, but direct API calls work.

---

## Adding a new provider

### OpenAI-compatible provider (most cases — two lines of config)

```python
# In config.py
OPENAI_COMPAT_PROVIDERS = {
    # ... existing entries ...

    "myprovider": {
        "api_key":  os.getenv("MYPROVIDER_API_KEY", ""),
        "base_url": "https://api.myprovider.com/v1",
    },
}
```

That's it. Use `myprovider/some-model-id` as the model name.

### Self-hosted example (vLLM)

```python
# In config.py
"myvllm": {
    "api_key":  "EMPTY",                     # vLLM accepts any non-empty string
    "base_url": "http://localhost:8000/v1",
},
```

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "myvllm/meta-llama/Llama-3.1-8B-Instruct",
  "messages": [{"role": "user", "content": "Hello!"}]
}'
```

### Non-compatible provider (Cohere, Vertex AI, etc.)

For providers that do NOT speak the OpenAI wire format:

1. Create `providers/myprovider_provider.py` extending `BaseProvider`
2. Implement `chat()`, `chat_stream()`, optionally `chat_full()` and `chat_stream_raw()` for tool support, and `embed()`
3. Add an `elif prefix == "myprovider":` branch in `get_provider()` in `main.py`
4. Add models to `PROVIDER_REGISTRY` if you want them in `/api/tags`

---

## Model naming

The model string sent by your client is `<prefix>/<model-id>`:

```
openai/gpt-4o
gemini/gemini-2.5-pro
anthropic/claude-sonnet-4-5
xai/grok-2
groq/llama-3.3-70b-versatile
mistral/mistral-large-latest
deepseek/deepseek-chat
together/meta-llama/Llama-3.3-70B-Instruct-Turbo
perplexity/sonar-pro
kimi/kimi-k2.6
azure/my-deployment-name
bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0
myvllm/meta-llama/Llama-3.1-8B-Instruct
```

---

## Azure OpenAI setup

Azure needs three extra variables:

```bash
AZURE_OPENAI_API_KEY=<from Azure portal -> Keys & Endpoint>
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

The part after `azure/` is your **deployment name** (not the underlying model
name). For deployments across multiple Azure resources, use
`AZURE_DEPLOYMENTS` in `config.py`.

---

## AWS Bedrock setup

Bedrock uses the standard AWS credential chain — no API key needed. Set one of:

```bash
# Option 1: explicit credentials
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Option 2: named profile
AWS_PROFILE=my-bedrock-profile
```

Or run on EC2/ECS/Lambda with an IAM role attached — boto3 picks it up
automatically.

The model ID after `bedrock/` is the Bedrock model ID or cross-region
inference profile ID:

```
bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0
bedrock/us.amazon.nova-pro-v1:0
bedrock/us.amazon.nova-lite-v1:0
bedrock/us.meta.llama3-1-70b-instruct-v1:0
```

> **Note:** You must have model access enabled in your AWS account for the
> models you want to use. Check the Bedrock console → Model access.

---

## Options pass-through

Ollama's `options` object is translated per provider:

| Ollama option | OpenAI-compat | Anthropic | Bedrock |
|---------------|---------------|-----------|---------|
| `temperature` | `temperature` | `temperature` | `temperature` |
| `top_p` | `top_p` | `top_p` | `topP` |
| `num_predict` | `max_tokens` | `max_tokens` | `maxTokens` |
| `stop` | `stop` | `stop_sequences` | `stopSequences` |

`tools` and `format` (JSON mode / JSON schema) on `/api/chat` are passed
through to providers that support them.

---

## Debug logging

Set `PROXY_DEBUG=1` to enable verbose request/response logging:

```bash
PROXY_DEBUG=1 uv run uvicorn main:app --host 0.0.0.0 --port 11434
```

You'll see structured logs for each request:
```
[DEBUG] REQ /v1/chat/completions | model=gemini/gemini-2.5-pro stream=True messages=10 tools=74 format=None
[DEBUG]   last_msg: role=user content=...
[DEBUG] RES /v1/chat/completions | status=200 finish=stop
```

This is useful for debugging client integrations (Copilot, Continue, etc.)
to see what params the client is sending and whether tools/streaming work.

---

## Usage examples

### curl — Ollama format

```bash
curl http://localhost:11434/api/chat \
  -d '{"model": "openai/gpt-4o-mini", "messages": [{"role":"user","content":"Hi"}]}'
```

### curl — OpenAI format

```bash
curl http://localhost:11434/v1/chat/completions \
  -d '{"model": "gemini/gemini-2.5-flash", "messages": [{"role":"user","content":"Hi"}]}'
```

### Python — ollama SDK

```python
import ollama

client = ollama.Client(host="http://localhost:11434")
resp = client.chat(model="openai/gpt-4o", messages=[{"role": "user", "content": "Hello!"}])
print(resp["message"]["content"])
```

### Python — OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="dummy")
resp = client.chat.completions.create(
    model="kimi/kimi-k2.6",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(resp.choices[0].message.content)
```

### LangChain

```python
from langchain_community.llms import Ollama

llm = Ollama(base_url="http://localhost:11434", model="groq/llama-3.3-70b-versatile")
print(llm.invoke("Explain transformers in one paragraph."))
```

### Open WebUI

Set the Ollama URL to `http://localhost:11434` in Settings → Connections.
All registered models appear in the model dropdown.

### GitHub Copilot

In VS Code settings, configure the Ollama provider with
`http://localhost:11434` and pick any registered model name.

---

## Supported endpoints

### Ollama protocol

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /` | ✓ | Returns "Ollama is running" |
| `GET /api/version` | ✓ | Version string |
| `GET /api/tags` | ✓ | All models from PROVIDER_REGISTRY + EXTRA_MODELS |
| `GET /api/ps` | ✓ | Returns empty list (no VRAM concept) |
| `POST /api/chat` | ✓ | Streaming + non-streaming, tools, format |
| `POST /api/generate` | ✓ | Streaming + non-streaming, format |
| `POST /api/embeddings` | ✓ | Legacy format |
| `POST /api/embed` | ✓ | New format (v0.1.33+) |
| `POST /api/show` | ✓ | Mock model info |
| `POST /api/pull` | mocked | Streams progress events |
| `DELETE /api/delete` | mocked | Returns 200 |
| `POST /api/copy` | mocked | Returns 200 |
| `POST /api/push` | 501 | Not applicable |
| `POST /api/create` | 501 | Not applicable |

### OpenAI protocol (for Copilot, OpenAI SDK clients)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /v1/chat/completions` | ✓ | Streaming SSE + non-streaming, tools, response_format |
| `GET /v1/models` | ✓ | Lists all registered models |

---

## Project structure

```
ollama-proxy/
├── main.py                          # FastAPI app + endpoint handlers
├── config.py                        # Keys, base URLs, model registry
├── requirements.txt
├── pyproject.toml
├── .env.example
└── providers/
    ├── base.py                      # Abstract BaseProvider
    ├── openai_compat_provider.py    # Generic adapter (OpenAI, Gemini, Groq, Kimi, ...)
    ├── anthropic_provider.py        # Anthropic / Claude (native SDK)
    ├── azure_provider.py            # Azure OpenAI (deployment-based routing)
    └── bedrock_provider.py          # AWS Bedrock (Converse API via boto3)
```
