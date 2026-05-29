# ollama-proxy

A lightweight server that **speaks the Ollama API protocol** but routes every
request to a cloud or self-hosted LLM backend.

Any tool that already works with Ollama — LangChain, LlamaIndex, Open WebUI,
Continue, Cursor, the `ollama` Python SDK — connects here with **zero code
changes**.

---

## How it works

```
Your App  ---->  POST /api/chat  (Ollama format)
                        |
                 ollama-proxy
                        |  routes by model-name prefix
       +----------------+----------------+------- ... -------+
  openai/*        gemini/*        anthropic/*           custom/*
  OpenAI API    Gemini API      Anthropic API     your vLLM / Ray server
```

The **model name prefix** is the only routing key — no extra config needed.

---

## Supported providers

### Cloud providers (built-in)

| Prefix | Provider | Auth |
|---|---|---|
| `openai/` | OpenAI | `OPENAI_API_KEY` |
| `gemini/` | Google Gemini | `GEMINI_API_KEY` |
| `anthropic/` | Anthropic / Claude | `ANTHROPIC_API_KEY` |
| `azure/` | Azure OpenAI | `AZURE_OPENAI_*` vars |
| `kimi/` | Kimi / Moonshot AI | `KIMI_API_KEY` |
| `xai/` | xAI / Grok | `XAI_API_KEY` |
| `groq/` | Groq | `GROQ_API_KEY` |
| `mistral/` | Mistral AI | `MISTRAL_API_KEY` |
| `deepseek/` | DeepSeek | `DEEPSEEK_API_KEY` |
| `together/` | Together AI | `TOGETHER_API_KEY` |
| `perplexity/` | Perplexity | `PERPLEXITY_API_KEY` |

### Self-hosted / custom OpenAI-compatible servers

Any server that exposes an OpenAI-compatible REST API can be plugged in with
**two lines in `config.py`** — no code changes, no new dependencies.

This includes:

| Server | Typical base_url |
|---|---|
| **vLLM** | `http://localhost:8000/v1` |
| **Ray Serve** (with vLLM or TGI backend) | `http://localhost:8000/v1` |
| **Hugging Face TGI** | `http://localhost:8080/v1` |
| **LM Studio** | `http://localhost:1234/v1` |
| **LocalAI** | `http://localhost:8080/v1` |
| **Ollama** (real instance) | `http://localhost:11434/v1` |
| **Llamafile** | `http://localhost:8080/v1` |
| **Jan** | `http://localhost:1337/v1` |
| **Any other OAI-compat server** | whatever `--host` / `--port` you set |

---

## Quick start

### 1. Install dependencies

```bash
cd ollama-proxy
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# open .env and fill in only the providers you need
```

### 3. Start the server

```bash
uvicorn main:app --host 0.0.0.0 --port 11434 --reload
```

Port **11434** is Ollama's default — clients think they are talking to a real
Ollama instance.

---

## Model naming

The model string sent by your client is `<prefix>/<model-id>`:

```
openai/gpt-4o
gemini/gemini-2.0-flash
anthropic/claude-3-5-sonnet-20241022
xai/grok-2
groq/llama-3.3-70b-versatile
mistral/mistral-large-latest
deepseek/deepseek-chat
together/meta-llama/Llama-3.3-70B-Instruct-Turbo
perplexity/sonar-pro
azure/my-deployment-name
myvllm/meta-llama/Llama-3.1-8B-Instruct   <-- custom self-hosted
```

---

## Adding a self-hosted server

This is the most powerful feature of the proxy. Any OpenAI-compatible server
can be added in two places:

### Step 1 — add to `config.py`

```python
OPENAI_COMPAT_PROVIDERS = {
    # ... existing entries ...

    # vLLM running locally
    "myvllm": {
        "api_key":  "EMPTY",                     # vLLM accepts any non-empty string
        "base_url": "http://localhost:8000/v1",
    },

    # Ray Serve cluster
    "raycluster": {
        "api_key":  os.getenv("RAY_API_KEY", "EMPTY"),
        "base_url": "http://ray-head-node:8000/v1",
    },

    # A second vLLM instance for a different model
    "vllm-prod": {
        "api_key":  os.getenv("VLLM_PROD_KEY", "EMPTY"),
        "base_url": "http://gpu-server-01:8000/v1",
    },
}
```

### Step 2 — add models to `PROVIDER_REGISTRY`

```python
PROVIDER_REGISTRY = [
    # ... existing entries ...
    "myvllm/meta-llama/Llama-3.1-8B-Instruct",
    "myvllm/Qwen/Qwen2.5-72B-Instruct",
    "raycluster/mistralai/Mistral-7B-Instruct-v0.3",
    "vllm-prod/microsoft/Phi-3-medium-128k-instruct",
]
```

That's it. The proxy picks up the new prefix automatically — no routing code
to touch, no restarts needed if using `--reload`.

### vLLM quick-start example

```bash
# Start vLLM (GPU server)
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --host 0.0.0.0 \
  --port 8000

# Add to config.py
# OPENAI_COMPAT_PROVIDERS["myvllm"] = {
#     "api_key": "EMPTY",
#     "base_url": "http://<gpu-server>:8000/v1"
# }

# Call through the proxy
curl http://localhost:11434/api/chat \
  -d '{
    "model": "myvllm/meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Ray Serve + vLLM example

```python
# ray_serve_app.py
from ray import serve
from vllm.entrypoints.openai.api_server import router as vllm_router

@serve.deployment
@serve.ingress(vllm_router)
class VLLMDeployment:
    pass

# deploy with:  serve run ray_serve_app:VLLMDeployment

# Then in config.py:
# "ray": {
#     "api_key":  "EMPTY",
#     "base_url": "http://localhost:8000/v1",
# }
```

---

## Usage examples

### curl

```bash
# Cloud model
curl http://localhost:11434/api/chat \
  -d '{"model": "openai/gpt-4o-mini", "messages": [{"role":"user","content":"Hi"}]}'

# Self-hosted vLLM model
curl http://localhost:11434/api/chat \
  -d '{"model": "myvllm/Llama-3.1-8B-Instruct", "messages": [{"role":"user","content":"Hi"}]}'

# List all registered models
curl http://localhost:11434/api/tags
```

### Python — ollama SDK

```python
import ollama

client = ollama.Client(host="http://localhost:11434")

# Switch between cloud and self-hosted by changing the model prefix only
for model in ["openai/gpt-4o", "myvllm/Llama-3.1-8B-Instruct", "groq/llama-3.3-70b-versatile"]:
    resp = client.chat(model=model, messages=[{"role": "user", "content": "Hello!"}])
    print(f"{model}: {resp['message']['content'][:80]}")
```

### LangChain

```python
from langchain_community.llms import Ollama

# Swap any model — cloud or local — with one string change
llm = Ollama(base_url="http://localhost:11434", model="myvllm/Llama-3.1-8B-Instruct")
print(llm.invoke("Explain transformers in one paragraph."))
```

### Open WebUI

In Open WebUI -> Settings -> Connections, set the Ollama URL to
`http://localhost:11434`. All prefixed model names appear in the model
dropdown, both cloud and self-hosted.

---

## Supported Ollama endpoints

| Endpoint | Status | Notes |
|---|---|---|
| `GET /` | live | Returns plain text "Ollama is running" |
| `GET /api/version` | live | Returns version string |
| `GET /api/tags` | live | All models from PROVIDER_REGISTRY |
| `GET /api/ps` | live | Returns `{"models":[]}` — keeps Open WebUI happy |
| `POST /api/chat` | live | Streaming + non-streaming, full token stats |
| `POST /api/generate` | live | Streaming + non-streaming, full token stats |
| `POST /api/embeddings` | live | Legacy format — OpenAI, Azure, Mistral |
| `POST /api/embed` | live | New format (v0.1.33+) — string or array input |
| `POST /api/show` | live | Mock model info — clients verify model exists here |
| `POST /api/pull` | mocked | Streams 3 progress events so clients don't hang |
| `DELETE /api/delete` | mocked | Returns 200 |
| `POST /api/copy` | mocked | Returns 200 |
| `POST /api/push` | 501 | Not applicable for a proxy |
| `POST /api/create` | 501 | Not applicable for a proxy |

---

## Azure OpenAI setup

Azure needs three extra variables:

```bash
AZURE_OPENAI_API_KEY=<from Azure portal -> Keys & Endpoint>
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

The part after `azure/` is your **deployment name** (the name you gave in
Azure AI Studio), not the underlying model name.

For deployments across multiple Azure resources, use `AZURE_DEPLOYMENTS` in
`config.py` — each entry can have its own key, endpoint, and API version.

---

## Options pass-through

Ollama's `options` object is translated per provider:

| Ollama option | OpenAI / compat | Gemini | Anthropic |
|---|---|---|---|
| `temperature` | `temperature` | `temperature` | `temperature` |
| `top_p` | `top_p` | `top_p` | `top_p` |
| `num_predict` | `max_tokens` | `max_output_tokens` | `max_tokens` |
| `stop` | `stop` | `stop_sequences` | `stop_sequences` |

---

## Project structure

```
ollama-proxy/
├── main.py                          # FastAPI app + all Ollama endpoint handlers
├── config.py                        # Keys, base URLs, model registry
├── requirements.txt
├── .env.example                     # Copy to .env, fill in your keys
└── providers/
    ├── base.py                      # Abstract BaseProvider
    ├── openai_provider.py           # OpenAI (native SDK)
    ├── openai_compat_provider.py    # Generic OAI-compatible (vLLM, Ray, Groq, xAI ...)
    ├── gemini_provider.py           # Google Gemini
    ├── anthropic_provider.py        # Anthropic / Claude
    ├── kimi_provider.py             # Kimi / Moonshot AI
    └── azure_provider.py            # Azure OpenAI
```

---

## Adding a brand new non-compatible provider

For providers that do NOT speak the OpenAI wire format (e.g. Cohere,
AWS Bedrock, Vertex AI):

1. Create `providers/myprovider_provider.py` extending `BaseProvider`
2. Implement `chat()`, `chat_stream()`, and optionally `embed()`
3. Add `API_KEYS["myprovider"]` entry in `config.py`
4. Add an `elif prefix == "myprovider":` branch in `get_provider()` in `main.py`
5. Add model names to `PROVIDER_REGISTRY` in `config.py`
