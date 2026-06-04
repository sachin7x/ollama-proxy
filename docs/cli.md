# CLI reference

The `ollama-proxy` command supports several subcommands. If no subcommand is
given, `serve` is used.

You can also invoke it as `python -m ollama_proxy`.

```text
ollama-proxy [-h] [--version] {serve,doctor,list-models,test} ...
```

## `serve` (default)

Run the proxy server.

```bash
ollama-proxy [serve] [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host HOST` | `0.0.0.0` | Bind host |
| `--port PORT` | `11434` | Bind port |
| `--debug` | off | Verbose request/response logging |
| `--reload` | off | Auto-reload on code changes (dev only) |
| `--config PATH` | – | YAML config file path |
| `--workers N` | `1` | Number of worker processes (production) |

Examples:

```bash
# Default — port 11434, info-level logs
ollama-proxy

# Debug logging on a custom port
ollama-proxy --port 8080 --debug

# Production with multiple workers
ollama-proxy --workers 4

# Use a YAML config file
ollama-proxy --config ./ollama-proxy.yaml

# Development with auto-reload
ollama-proxy --reload --debug
```

Equivalent env vars: `PROXY_HOST`, `PROXY_PORT`, `PROXY_DEBUG=1`,
`PROXY_CONFIG_FILE`.

## `doctor`

One-shot health check: validates configuration and pings each configured
OpenAI-compatible provider's `/models` endpoint.

```bash
ollama-proxy doctor
```

Returns exit code `0` if everything is healthy, non-zero if any configured
provider is unreachable or unauthenticated.

Use this when:

- Setting up the proxy for the first time
- Debugging "request failed" errors from a client
- In CI/CD before deploying

## `list-models`

Print all configured models grouped by provider, plus the list of
OpenAI-compatible providers and which ones have an API key.

```bash
ollama-proxy list-models
```

## `test`

Send a one-off chat request to a specific model and print the response.

```bash
ollama-proxy test <model> [--prompt TEXT]
```

Examples:

```bash
# Default prompt
ollama-proxy test openai/gpt-4o-mini

# Custom prompt
ollama-proxy test gemini/gemini-2.5-flash --prompt "What is the capital of France?"
```

Useful for validating that a provider works end-to-end without standing up the
full server.

## `--version`

```bash
ollama-proxy --version
# ollama-proxy 0.1.0
```
