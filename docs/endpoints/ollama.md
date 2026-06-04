# Ollama protocol endpoints

The proxy implements the Ollama REST API at `/api/*`. Pointing any
Ollama-aware client at `http://localhost:11434` makes it talk to whichever
upstream the model prefix routes to.

## Status overview

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /` | ✓ | "Ollama is running" |
| `GET /api/version` | ✓ | Reports `0.6.5` (some clients require ≥0.6.4) |
| `GET /api/tags` | ✓ | All models from registry + `EXTRA_MODELS` + YAML |
| `GET /api/ps` | ✓ | Always empty (no VRAM concept for cloud) |
| `POST /api/show` | ✓ | Mock model info |
| `POST /api/chat` | ✓ | Streaming + non-streaming, `tools`, `format` |
| `POST /api/generate` | ✓ | Streaming + non-streaming, `format` |
| `POST /api/embed` | ✓ | New format (v0.1.33+) |
| `POST /api/embeddings` | ✓ | Legacy format |
| `POST /api/pull` | mocked | Streams 3 progress events |
| `DELETE /api/delete` | mocked | Returns 200 |
| `POST /api/copy` | mocked | Returns 200 |
| `POST /api/push` | 501 | Not applicable for a proxy |
| `POST /api/create` | 501 | Not applicable for a proxy |

## `POST /api/chat`

Multi-turn chat completion.

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "openai/gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": true,
  "options": {
    "temperature": 0.7,
    "num_predict": 200
  },
  "tools": [...],
  "format": "json"
}'
```

Streaming response is NDJSON (one JSON object per line) with `done: false`
chunks ending in a final `done: true` chunk that includes timing/token stats.

## `POST /api/generate`

Single-prompt completion. Same options as `/api/chat`, but the response field
is `response` (text) instead of `message` (object).

## `POST /api/embed`

Generate embeddings for a single string or array of strings.

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "openai/text-embedding-3-small",
  "input": "Why is the sky blue?"
}'
```

Response:

```json
{
  "model": "openai/text-embedding-3-small",
  "embeddings": [[0.01, -0.001, ...]],
  "total_duration": 0,
  "load_duration": 0,
  "prompt_eval_count": 5
}
```

`POST /api/embeddings` is the legacy single-string variant (returns
`{"embedding": [...]}`).

## Options pass-through

The Ollama `options` object is mapped to provider-specific names:

| Ollama option | OpenAI-compat | Anthropic | Bedrock |
|---------------|---------------|-----------|---------|
| `temperature` | `temperature` | `temperature` | `temperature` |
| `top_p` | `top_p` | `top_p` | `topP` |
| `num_predict` | `max_tokens` | `max_tokens` | `maxTokens` |
| `stop` | `stop` | `stop_sequences` | `stopSequences` |

`tools` and `format` (JSON mode / JSON schema) are passed through to
providers that support them.

## Model registration

Any `<prefix>/<model-id>` works as long as the prefix is configured. The
registry only controls what shows up in `/api/tags`. See
[Adding models](../config/models.md).
