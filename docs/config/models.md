# Adding models

Models can be registered three ways — direct API call, env var, or YAML.

The model registry is **only used for `/api/tags` discovery** (so your model
names appear in client dropdowns). You can call any `prefix/model-id`
without registering it, as long as the prefix is configured.

## Method 1 — Direct API call (no registration)

Any `<prefix>/<model-id>` works as long as the prefix is configured:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "openai/gpt-5-preview",
  "messages": [{"role": "user", "content": "Hi"}]
}'
```

The model just won't appear in `GET /api/tags` — useful for ad-hoc model
testing without restart.

## Method 2 — `EXTRA_MODELS` env var

Comma-separated list, no editing of any file:

```bash
export EXTRA_MODELS="openai/gpt-5,gemini/gemini-3-pro,kimi/kimi-k2.7"
ollama-proxy
```

These appear in `/api/tags` and `ollama-proxy list-models`.

## Method 3 — YAML config

```yaml
# ollama-proxy.yaml
models:
  - openai/gpt-5
  - gemini/gemini-3-pro
  - myvllm/meta-llama/Llama-3.1-70B
```

```bash
ollama-proxy --config ollama-proxy.yaml
```

## Default registry

The proxy ships with a small default list of well-known models. See the
[source](https://github.com/skamalj/ollama-proxy/blob/master/ollama_proxy/config.py)
for the current list.

To get a quick view:

```bash
ollama-proxy list-models
```

## Precedence

Models from all three sources are merged. Duplicates are skipped:

```
default registry  →  EXTRA_MODELS  →  YAML config
```

The order doesn't matter for routing — the registry is just for discovery.
