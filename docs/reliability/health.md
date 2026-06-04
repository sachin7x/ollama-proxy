# Health checks

Two endpoints, plus a CLI command, for monitoring and probing.

## `GET /health`

Lightweight — does not hit upstream providers. Use this for load-balancer
liveness probes, container health checks, etc.

```bash
curl http://localhost:11434/health
```

Response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "providers": {
    "openai_compat": ["openai", "gemini", "kimi", "xai", "groq", "mistral", "deepseek", "together", "perplexity"],
    "anthropic": true,
    "azure": false,
    "bedrock": true
  },
  "models_registered": 38
}
```

`anthropic`, `azure`, `bedrock` are booleans indicating whether the
required env vars are set (not whether they're actually working).

## `GET /health/providers`

Pings every OpenAI-compatible provider's `/models` endpoint. Slower (one
HTTP round-trip per provider, in parallel) but tells you which providers
are actually reachable and authenticated.

```bash
curl http://localhost:11434/health/providers
```

Response (abbreviated):

```json
{
  "overall": "degraded",
  "providers": {
    "openai":     { "status": "ok",           "http_status": 200, "url": "https://api.openai.com/v1/models" },
    "gemini":     { "status": "ok",           "http_status": 200, "url": "https://generativelanguage.googleapis.com/v1beta/openai/models" },
    "kimi":       { "status": "ok",           "http_status": 200, "url": "https://api.moonshot.ai/v1/models" },
    "groq":       { "status": "unconfigured", "detail": "no API key" },
    "perplexity": { "status": "error",        "http_status": 401, "url": "https://api.perplexity.ai/models" }
  }
}
```

`overall` is `ok` if every configured provider returns ok, otherwise
`degraded`.

This is a deeper check than `/health`. Use it for diagnostic dashboards —
running it every few seconds against many providers can rack up rate limits.

## `ollama-proxy doctor`

The same connectivity check as `/health/providers`, plus environment-variable
sanity checks, all from the CLI:

```bash
ollama-proxy doctor
```

Returns exit code `0` if everything is healthy, non-zero on any failure.
Useful in CI/CD before deployments and when first setting up the proxy.

See the [CLI reference](../cli.md#doctor) for sample output.
