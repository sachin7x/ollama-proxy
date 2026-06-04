# YAML config file

For complex setups (multiple providers, retries, fallbacks), a YAML config
file is cleaner than env vars.

## Loading

```bash
ollama-proxy --config ollama-proxy.yaml
```

Or set the path via env:

```bash
export PROXY_CONFIG_FILE=ollama-proxy.yaml
ollama-proxy
```

If neither is set, the proxy looks for `./ollama-proxy.yaml` then
`./ollama-proxy.yml` in the working directory.

YAML config layers **on top of** env-var defaults. Built-in providers
already work via env vars; the YAML file lets you override or add to them.

## Schema

```yaml
providers:
  <name>:
    api_key: <string>          # Bearer token; ${ENV_VAR} expansion supported
    base_url: <string>         # Required for new providers
    retries: <int>             # Optional, default 0
    fallback: <prefix/model>   # Optional, used after retries are exhausted

models:
  - <prefix>/<model-id>        # Optional list; added to /api/tags
```

`${ENV_VAR}` references are expanded at load time.

## Sample

A complete example with multiple providers, a self-hosted server, and a
fallback chain:

```yaml
# ollama-proxy.yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    retries: 2
    fallback: groq/llama-3.3-70b-versatile     # if OpenAI is rate-limited

  groq:
    api_key: ${GROQ_API_KEY}

  myvllm:
    api_key: EMPTY                              # vLLM accepts any non-empty value
    base_url: http://localhost:8000/v1

  ray:
    api_key: ${RAY_API_KEY}
    base_url: http://ray-head:8000/v1
    retries: 1
    fallback: openai/gpt-4o-mini

models:
  - openai/gpt-4o
  - openai/gpt-4o-mini
  - groq/llama-3.3-70b-versatile
  - myvllm/meta-llama/Llama-3.1-8B-Instruct
```

See [`ollama-proxy.example.yaml`](https://github.com/skamalj/ollama-proxy/blob/master/ollama-proxy.example.yaml)
in the repo for the latest reference.

## Provider settings

| Field | Type | Description |
|-------|------|-------------|
| `api_key` | string | Required for cloud providers; `EMPTY` for self-hosted |
| `base_url` | string | Required for new providers; optional for built-ins |
| `retries` | int | Number of retries before falling back (default 0) |
| `fallback` | string | Model to use after retries fail, e.g. `openai/gpt-4o-mini` |

See [Retry & fallback](../reliability/retry-fallback.md) for the retry
behavior in detail.
