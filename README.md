# ollama-proxy

[![PyPI version](https://img.shields.io/pypi/v/ollama-proxy-plus.svg)](https://pypi.org/project/ollama-proxy-plus/)
[![Python versions](https://img.shields.io/pypi/pyversions/ollama-proxy-plus.svg)](https://pypi.org/project/ollama-proxy-plus/)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://skamalj.github.io/ollama-proxy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A lightweight server that **speaks the Ollama API protocol** and routes every
request to a cloud or self-hosted LLM backend.

> Distributed on PyPI as **`ollama-proxy-plus`** (the `ollama-proxy` name was
> taken). Install with `pip install ollama-proxy-plus`. Everything else —
> import path, CLI command, endpoints — stays as `ollama-proxy`.

📚 **Full documentation: https://skamalj.github.io/ollama-proxy/**

Any tool that already works with Ollama — Open WebUI, Continue, Cursor,
GitHub Copilot, LangChain, LlamaIndex, the `ollama` Python SDK — connects with
**zero code changes**.

```
Your App  ---->  POST /api/chat            (Ollama protocol)
         ---->  POST /v1/chat/completions  (OpenAI protocol)
                        |
                 ollama-proxy
                        |  routes by model-name prefix
       +----------------+----------------+------- ... -------+
  openai/*        gemini/*        anthropic/*           custom/*
  OpenAI API    Gemini API      Anthropic API     your vLLM / Ray server
```

The **model name prefix** is the only routing key. The proxy speaks **two wire
formats simultaneously** — the Ollama protocol on `/api/*` and the OpenAI
protocol on `/v1/*` — so it works with both ecosystems.

---

## Install

```bash
# Core (OpenAI / Gemini / xAI / Groq / Mistral / DeepSeek / Together / Perplexity / Kimi / vLLM / etc.)
pip install ollama-proxy-plus

# With Anthropic SDK
pip install "ollama-proxy-plus[anthropic]"

# With AWS Bedrock support
pip install "ollama-proxy-plus[bedrock]"

# Everything
pip install "ollama-proxy-plus[all]"
```

Or run without installing using `uv`:

```bash
uvx ollama-proxy-plus
```

## Quick start

```bash
# 1. Set API keys for the providers you'll use
export OPENAI_API_KEY=sk-...
export GEMINI_API_KEY=AIza...

# 2. Start the proxy on port 11434 (Ollama's default)
ollama-proxy

# 3. Use any Ollama-compatible client pointed at http://localhost:11434
curl http://localhost:11434/api/chat \
  -d '{"model": "openai/gpt-4o-mini", "messages": [{"role":"user","content":"Hi"}]}'
```

Optional: copy `.env.example` to `.env` and put keys there instead of exporting them.

---

## CLI

```
ollama-proxy [serve]    # run the proxy (default subcommand)
ollama-proxy doctor     # check config + provider connectivity
ollama-proxy list-models
ollama-proxy test openai/gpt-4o-mini --prompt "Say hello"
```

`serve` flags:
- `--host 0.0.0.0` (default)
- `--port 11434` (default)
- `--debug` — verbose request/response logging
- `--reload` — auto-reload on code changes (dev)
- `--config path.yaml` — load YAML config
- `--workers N` — number of worker processes

Or `python -m ollama_proxy ...` works too.

---

## Adding models

Three ways, in increasing permanence:

### 1. Direct call (no registration)
Any `<prefix>/<model-id>` works as long as the prefix is configured. The model
just won't appear in `/api/tags` discovery.

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "openai/gpt-5-preview",
  "messages": [{"role": "user", "content": "Hi"}]
}'
```

### 2. `EXTRA_MODELS` env var
```bash
export EXTRA_MODELS="openai/gpt-5,gemini/gemini-3-pro,kimi/kimi-k2.7"
ollama-proxy
```

### 3. YAML config file
```yaml
# ollama-proxy.yaml
models:
  - openai/gpt-5
  - gemini/gemini-3-pro
```
```bash
ollama-proxy --config ollama-proxy.yaml
```

---

## Adding providers

### OpenAI-compatible (most providers, including self-hosted)

**Option A — environment variables (auto-discovered):**
```bash
export PROVIDERS_VLLM_API_KEY=EMPTY
export PROVIDERS_VLLM_BASE_URL=http://localhost:8000/v1
ollama-proxy
```
Use `vllm/<model-id>` in your client. No code changes needed.

**Option B — YAML config:**
```yaml
providers:
  myvllm:
    api_key: EMPTY
    base_url: http://localhost:8000/v1
  ray:
    api_key: ${RAY_API_KEY}
    base_url: http://ray-head:8000/v1
    retries: 2
    fallback: openai/gpt-4o-mini
```

### Non-compatible provider (Cohere, Vertex AI, etc.)

For wire formats incompatible with OpenAI:
1. Subclass `BaseProvider` in `ollama_proxy/providers/myprovider_provider.py`
2. Implement `chat()`, `chat_stream()`, optionally `chat_full()` and
   `chat_stream_raw()` for tool support, and `embed()`
3. Add a routing branch in `ollama_proxy/server.py::get_provider()`

---

## Built-in providers

### OpenAI-compatible (one adapter, many providers)

| Prefix | Provider | Base URL | Env Variable |
|--------|----------|----------|--------------|
| `openai/` | OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `gemini/` | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY` |
| `xai/` | xAI / Grok | `https://api.x.ai/v1` | `XAI_API_KEY` |
| `groq/` | Groq | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` |
| `mistral/` | Mistral AI | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` |
| `deepseek/` | DeepSeek | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |
| `together/` | Together AI | `https://api.together.xyz/v1` | `TOGETHER_API_KEY` |
| `perplexity/` | Perplexity | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` |
| `kimi/` | Kimi / Moonshot | `https://api.moonshot.ai/v1` | `KIMI_API_KEY` |

> Endpoints can change. Verify against each provider's docs before relying on them in production.

### Self-hosted servers

Any OpenAI-compatible REST server works the same way (typical defaults):

| Server | Base URL |
|--------|----------|
| vLLM, Ray Serve (vLLM backend) | `http://localhost:8000/v1` |
| Hugging Face TGI, LocalAI, Llamafile | `http://localhost:8080/v1` |
| LM Studio | `http://localhost:1234/v1` |
| Ollama (real instance) | `http://localhost:11434/v1` |
| Jan | `http://localhost:1337/v1` |

### Native SDK providers

| Prefix | Provider | Auth | Install |
|--------|----------|------|---------|
| `anthropic/` | Anthropic / Claude | `ANTHROPIC_API_KEY` | `pip install ollama-proxy-plus[anthropic]` |
| `azure/` | Azure OpenAI | `AZURE_OPENAI_*` vars | (core) |
| `bedrock/` | AWS Bedrock | AWS credential chain | `pip install ollama-proxy-plus[bedrock]` |

---

## Azure OpenAI

```bash
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```
The part after `azure/` is your deployment name. For multi-resource setups,
populate `AZURE_DEPLOYMENTS` in `config.py`.

## AWS Bedrock

Uses the standard AWS credential chain — no API key. Just have AWS creds
configured via env vars, profile, or IAM role:

```bash
AWS_REGION=us-east-1
# plus access keys, profile, or IAM role
```

Use the model ID or cross-region inference profile after `bedrock/`:
```
bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0
bedrock/us.amazon.nova-pro-v1:0
bedrock/us.meta.llama3-1-70b-instruct-v1:0
```

> Enable model access in the Bedrock console first.

---

## YAML configuration

The proxy reads `--config <file>` or `$PROXY_CONFIG_FILE`. See
[`ollama-proxy.example.yaml`](ollama-proxy.example.yaml). Highlights:

```yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    retries: 2                            # transient-error retries
    fallback: groq/llama-3.3-70b-versatile  # used after retries exhausted

  myvllm:
    api_key: EMPTY
    base_url: http://localhost:8000/v1

models:
  - openai/gpt-4o
  - myvllm/meta-llama/Llama-3.1-8B-Instruct
```

`${ENV_VAR}` references are expanded. YAML config layers on top of env-var
defaults.

---

## Retry & fallback

Any provider can have `retries` and `fallback`. On transient failures
(429, 5xx, timeouts, connection errors) the proxy retries with exponential
backoff, then falls back to the configured model:

```yaml
providers:
  kimi:
    retries: 2
    fallback: openai/gpt-4o-mini
```

Set per provider; client sees a successful response from the fallback if
the primary is degraded.

---

## Health checks

| Endpoint | Description |
|----------|-------------|
| `/health` | Lightweight: status, version, configured providers, model count |
| `/health/providers` | Pings each OpenAI-compat provider's `/models` endpoint |

Useful for monitoring, load-balancer probes, and quickly seeing which
provider is down right now.

---

## Logging & observability

Every request gets a unique `x-request-id` (returned in response headers and
included in every log line for that request).

```bash
# Verbose request/response logs
ollama-proxy --debug

# JSON-formatted logs (for log aggregators)
PROXY_LOG_JSON=1 ollama-proxy --debug
```

Sample debug output:
```
2026-06-04 12:30:15 [DEBUG] [a3f2b1c4d5e6] ollama-proxy: REQ /v1/chat/completions model=gemini/gemini-2.5-pro stream=True messages=10 tools=74 format=None
2026-06-04 12:30:18 [DEBUG] [a3f2b1c4d5e6] ollama-proxy: RES /v1/chat/completions status=200 finish=stop
```

Run `ollama-proxy doctor` to validate your configuration and check
upstream connectivity in one shot.

---

## Endpoints

### Ollama protocol
| Endpoint | Notes |
|----------|-------|
| `GET /` | "Ollama is running" |
| `GET /api/version` | Reports 0.6.5 |
| `GET /api/tags` | All registered models |
| `GET /api/ps` | Always empty (no VRAM concept) |
| `POST /api/chat` | Streaming + non-streaming, `tools`, `format` |
| `POST /api/generate` | Streaming + non-streaming, `format` |
| `POST /api/embed` / `/api/embeddings` | Both formats supported |
| `POST /api/show` | Model details |
| `POST /api/pull` | Mocked (3 progress events) |

### OpenAI protocol (Copilot, OpenAI SDK, Continue)
| Endpoint | Notes |
|----------|-------|
| `POST /v1/chat/completions` | Streaming SSE + non-streaming, `tools`, `response_format` |
| `GET /v1/models` | Lists registered models |

### Health
| Endpoint | Notes |
|----------|-------|
| `GET /health` | Basic status |
| `GET /health/providers` | Connectivity check across all OpenAI-compat providers |

---

## Usage examples

### ollama Python SDK
```python
import ollama
client = ollama.Client(host="http://localhost:11434")
resp = client.chat(model="openai/gpt-4o", messages=[{"role": "user", "content": "Hi"}])
print(resp["message"]["content"])
```

### OpenAI SDK
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="dummy")
resp = client.chat.completions.create(
    model="kimi/kimi-k2.6",
    messages=[{"role": "user", "content": "Hi"}],
)
print(resp.choices[0].message.content)
```

### Open WebUI
Settings → Connections → Ollama URL: `http://localhost:11434`. All registered
models appear in the dropdown.

### GitHub Copilot
In VS Code settings, configure the Ollama provider with
`http://localhost:11434` and pick any registered model.

---

## Development

```bash
git clone https://github.com/skamalj/ollama-proxy
cd ollama-proxy
uv sync --extra all
uv run ollama-proxy --debug
```

Run tests:
```bash
uv run pytest
```

---

## Project structure

```
ollama_proxy/
├── __init__.py              # Package version + app re-export
├── __main__.py              # python -m ollama_proxy
├── cli.py                   # CLI entry point
├── server.py                # FastAPI app + endpoint handlers
├── config.py                # Config loading (env + YAML + auto-discovery)
├── logging_config.py        # Structured logging + correlation IDs
├── retry.py                 # Retry / fallback orchestration
├── commands/                # CLI subcommands
│   ├── doctor.py
│   ├── list_models.py
│   └── test.py
└── providers/
    ├── base.py
    ├── openai_compat_provider.py   # OpenAI, Gemini, Groq, Kimi, vLLM, ...
    ├── anthropic_provider.py       # Anthropic / Claude
    ├── azure_provider.py           # Azure OpenAI
    └── bedrock_provider.py         # AWS Bedrock (Converse API)
```

---

## License

MIT — see [LICENSE](LICENSE).
