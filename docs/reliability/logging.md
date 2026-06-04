# Logging & tracing

The proxy uses structured logging with per-request correlation IDs.

## Quick toggle

=== "Verbose text logs"

    ```bash
    ollama-proxy --debug
    # or
    PROXY_DEBUG=1 ollama-proxy
    ```

=== "JSON logs"

    ```bash
    PROXY_LOG_JSON=1 ollama-proxy --debug
    ```

## Correlation IDs

Every incoming HTTP request gets a unique `x-request-id` (12 hex chars).
The ID is:

- Returned in the response header (`x-request-id`)
- Included in every log line emitted while handling that request
- Honored if the client sends an `x-request-id` header (passed through
  unchanged for end-to-end tracing)

So `curl -i ...` shows the ID, and `grep <id>` in your logs gives you the
full picture for any single request.

## Sample output

Text format (default):

```
2026-06-04 12:30:15 [DEBUG] [a3f2b1c4d5e6] ollama-proxy: REQ /v1/chat/completions model=gemini/gemini-2.5-pro stream=True messages=10 tools=74 format=None
2026-06-04 12:30:15 [DEBUG] [a3f2b1c4d5e6] ollama-proxy: POST /v1/chat/completions -> 200 (3245.7ms)
2026-06-04 12:30:18 [DEBUG] [a3f2b1c4d5e6] ollama-proxy: RES /v1/chat/completions status=200 finish=stop
```

JSON format (`PROXY_LOG_JSON=1`):

```json
{"ts":"2026-06-04T12:30:15Z","level":"DEBUG","logger":"ollama-proxy","request_id":"a3f2b1c4d5e6","msg":"REQ /v1/chat/completions model=gemini/gemini-2.5-pro stream=True messages=10 tools=74 format=None"}
{"ts":"2026-06-04T12:30:15Z","level":"DEBUG","logger":"ollama-proxy","request_id":"a3f2b1c4d5e6","msg":"POST /v1/chat/completions -> 200 (3245.7ms)"}
{"ts":"2026-06-04T12:30:18Z","level":"DEBUG","logger":"ollama-proxy","request_id":"a3f2b1c4d5e6","msg":"RES /v1/chat/completions status=200 finish=stop"}
```

## What gets logged with `--debug`

- Incoming request: HTTP method, path, status, latency, request ID
- Application request summary: model, stream flag, message count, tool count, format
- Last user message preview (first 100 chars) — useful for matching logs
  to user input
- Response summary: status code, finish reason, tokens (when known)
- Streaming errors with full traceback
- Retry attempts and fallback transitions

## What gets logged without `--debug`

Just request lines (`POST /api/chat -> 200 (1234.5ms)`), warnings, and
errors. Quiet enough for production.

Library noise (httpx, urllib3, boto3, etc.) is suppressed below WARNING
unless `--debug` is on.

## Plugging into log aggregators

For Datadog, Elasticsearch, Cloud Logging, etc., enable JSON mode:

```bash
PROXY_LOG_JSON=1 PROXY_DEBUG=1 ollama-proxy
```

Then point your collector at stdout. Every line is a self-contained JSON
object with `ts`, `level`, `logger`, `request_id`, `msg`, plus any
structured fields.
