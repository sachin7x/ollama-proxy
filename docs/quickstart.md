# Quick start

## 1. Install

=== "Core only"

    ```bash
    pip install ollama-proxy-plus
    ```

    Includes built-in support for OpenAI, Gemini, xAI, Groq, Mistral, DeepSeek,
    Together, Perplexity, Kimi, and any OpenAI-compatible server (vLLM, Ray
    Serve, LM Studio, …).

=== "With Anthropic"

    ```bash
    pip install "ollama-proxy-plus[anthropic]"
    ```

=== "With AWS Bedrock"

    ```bash
    pip install "ollama-proxy-plus[bedrock]"
    ```

=== "Everything"

    ```bash
    pip install "ollama-proxy-plus[all]"
    ```

=== "Run without installing (uv)"

    ```bash
    uvx ollama-proxy-plus
    ```

## 2. Set API keys

Set environment variables for the providers you want to use:

```bash
export OPENAI_API_KEY=sk-...
export GEMINI_API_KEY=AIza...
export ANTHROPIC_API_KEY=sk-ant-...
```

Or copy `.env.example` to `.env` and fill it in — the proxy reads `.env`
automatically.

See [Environment variables](config/env.md) for the full list.

## 3. Start the server

```bash
ollama-proxy
```

By default the proxy listens on `0.0.0.0:11434` — Ollama's standard port.
Clients pointed at `http://localhost:11434` will think they're talking to a
real Ollama instance.

```bash
ollama-proxy --port 11434 --debug          # verbose logs
ollama-proxy --config ollama-proxy.yaml    # YAML config
```

See the [CLI reference](cli.md) for all flags.

## 4. Make a request

The model string `<prefix>/<model-id>` selects the upstream provider:

=== "curl (Ollama format)"

    ```bash
    curl http://localhost:11434/api/chat -d '{
      "model": "openai/gpt-4o-mini",
      "messages": [{"role": "user", "content": "Hello!"}]
    }'
    ```

=== "curl (OpenAI format)"

    ```bash
    curl http://localhost:11434/v1/chat/completions -d '{
      "model": "gemini/gemini-2.5-flash",
      "messages": [{"role": "user", "content": "Hello!"}]
    }'
    ```

=== "Python (ollama SDK)"

    ```python
    import ollama
    client = ollama.Client(host="http://localhost:11434")
    resp = client.chat(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    print(resp["message"]["content"])
    ```

=== "Python (OpenAI SDK)"

    ```python
    from openai import OpenAI
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="dummy")
    resp = client.chat.completions.create(
        model="kimi/kimi-k2.6",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    print(resp.choices[0].message.content)
    ```

## 5. Validate setup

The `doctor` subcommand checks your config and pings each provider:

```bash
ollama-proxy doctor
```

```text
ollama-proxy doctor
==================================================

Environment:
  ✗ PROXY_DEBUG                    (unset)
  ✗ EXTRA_MODELS                   (unset)
  ✗ PROXY_CONFIG_FILE              (unset)

Native-SDK providers:
  ✓ anthropic                      key set
  ✗ azure                          AZURE_OPENAI_* not set
  ✓ bedrock                        region=us-east-1

OpenAI-compatible providers:
  ✓ openai                         reachable (https://api.openai.com/v1/models)
  ✓ gemini                         reachable (https://generativelanguage.googleapis.com/v1beta/openai/models)
  ✗ groq                           no API key set (skipped connectivity)
  ...
```

See the [CLI reference](cli.md#doctor) for more.

## What's next?

- [Providers](providers/index.md) — pick your backends
- [Adding models](config/models.md) — three ways to register models
- [Client examples](examples.md) — Copilot, Continue, Open WebUI setups
- [Reliability](reliability/retry-fallback.md) — retry and fallback config
