# Retry & fallback

The proxy can retry transient failures and fall back to a different model
when retries are exhausted. Configured per-provider.

## What counts as transient?

The retry/fallback logic triggers on:

- HTTP `429` (rate limit) and `5xx` from upstream
- Connection errors and timeouts
- Provider-specific errors flagged as transient (e.g. boto3
  `ThrottlingException`)

Non-transient errors (4xx other than 429, validation errors, auth failures)
fail immediately — no retry, no fallback.

## Configuration

In YAML config:

```yaml
providers:
  openai:
    retries: 2
    fallback: groq/llama-3.3-70b-versatile

  kimi:
    retries: 1
    fallback: openai/gpt-4o-mini

  myvllm:
    api_key: EMPTY
    base_url: http://localhost:8000/v1
    retries: 3
    # No fallback — just retries
```

| Field | Default | Description |
|-------|---------|-------------|
| `retries` | `0` | Attempts after the first failure |
| `fallback` | – | `prefix/model` to use after retries are exhausted |

## How it works

```
                                 ┌─ success
                                 │
[primary]  ──[transient]──►  retry (with backoff) ──[transient]──►  retry  ──...
                                                                     │
                                                                     │  ✗ retries exhausted
                                                                     ▼
                                                                  [fallback]
                                                                     │
                                                                     ├─ success  →  return as if from primary
                                                                     └─ failure  →  raise
```

- Backoff is exponential, capped at 10s: `1s, 2s, 4s, 8s, 10s, 10s, …`
- The fallback gets one attempt (no recursive retry on the fallback itself).
- Both Ollama (`/api/chat`, `/api/generate`) and OpenAI
  (`/v1/chat/completions`) endpoints respect this.
- The client sees a successful response from the fallback if the primary
  fails — there's no special "fallback used" indicator in the response.

## When to use fallback

- **Rate-limited providers** — Kimi, Groq, and free tiers can throttle. A
  fallback to a paid OpenAI/Anthropic keeps Copilot working.
- **Local backends** — vLLM/Ray with a cloud fallback if the local server
  is overloaded or down for a deploy.
- **Cost optimization** — try a cheap model first, fall back to a stronger
  model only when it errors. (Note: only fallback on errors, not on
  output quality.)

## Logs

Retries and fallbacks are logged at WARNING level (visible without
`--debug`):

```
[abc123def456] ollama-proxy.retry: transient error from kimi (attempt 1/3): RateLimitError: 429. retrying in 1s
[abc123def456] ollama-proxy.retry: transient error from kimi after 3 attempts: RateLimitError: 429
[abc123def456] ollama-proxy.retry: falling back from kimi/kimi-k2.6 to openai/gpt-4o-mini
```

Use the `x-request-id` header to correlate retries with the originating
request. See [Logging & tracing](logging.md).
