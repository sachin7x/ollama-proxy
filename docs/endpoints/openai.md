# OpenAI protocol endpoints

The proxy also implements the OpenAI Chat Completions API at `/v1/*`. This
is what GitHub Copilot, the OpenAI Python SDK, Continue, Cursor, and many
other tools speak.

| Endpoint | Notes |
|----------|-------|
| `POST /v1/chat/completions` | Streaming SSE + non-streaming, `tools`, `response_format` |
| `GET /v1/models` | Lists registered models in OpenAI format |

## `POST /v1/chat/completions`

```bash
curl http://localhost:11434/v1/chat/completions -d '{
  "model": "gemini/gemini-2.5-flash",
  "messages": [{"role": "user", "content": "Hello!"}],
  "stream": false,
  "tools": [...],
  "response_format": {"type": "json_object"}
}'
```

Non-streaming response (truncated):

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1780488000,
  "model": "gemini/gemini-2.5-flash",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello!"},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6}
}
```

## Streaming

When `stream: true`, responses are Server-Sent Events:

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

`tool_calls` deltas are streamed in the same format the OpenAI SDK expects,
so Copilot and similar tools can drive function-calling flows correctly.

## Parameter handling

| OpenAI param | Behavior |
|--------------|----------|
| `model` | `<prefix>/<model-id>` — required |
| `messages` | Standard OpenAI format, passed through |
| `tools` | Passed through to providers that support it |
| `response_format` | `json_object` and `json_schema` passed through |
| `max_tokens` / `max_completion_tokens` | Mapped to provider's max-tokens param |
| `stop` | Passed through |
| `temperature` / `top_p` | **Skipped** — see note below |

!!! note "Why temperature isn't forwarded"
    Some models (notably Kimi K2.5+) reject any `temperature` value other
    than `1`. Copilot and other clients tend to set a default temperature
    like `0.7`, which would cause hard failures for those models.

    The proxy intentionally drops `temperature` and `top_p` from the
    `/v1/chat/completions` endpoint to avoid this. If you need custom
    temperature, use the Ollama `options` object on `/api/chat` instead.

## Provider-specific behavior

### Kimi
The proxy automatically sets `thinking: {type: "disabled"}` for `kimi/`
models on this endpoint. Copilot and similar clients can't render
reasoning tokens, so disabling them keeps responses clean.

## `GET /v1/models`

Returns all registered models in OpenAI list format:

```json
{
  "object": "list",
  "data": [
    {"id": "openai/gpt-4o", "object": "model", "owned_by": "openai", "created": 1700000000},
    {"id": "gemini/gemini-2.5-pro", "object": "model", "owned_by": "gemini", "created": 1700000000}
  ]
}
```

## See also

- [Logging & tracing](../reliability/logging.md) — every response has an
  `x-request-id` header you can grep for in logs.
- [Retry & fallback](../reliability/retry-fallback.md) — applies to this
  endpoint just like Ollama protocol calls.
