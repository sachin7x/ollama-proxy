# ollama-proxy

[![PyPI version](https://img.shields.io/pypi/v/ollama-proxy-plus.svg)](https://pypi.org/project/ollama-proxy-plus/)
[![Python versions](https://img.shields.io/pypi/pyversions/ollama-proxy-plus.svg)](https://pypi.org/project/ollama-proxy-plus/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/skamalj/ollama-proxy/blob/master/LICENSE)

A lightweight server that **speaks the Ollama API protocol** and routes every
request to a cloud or self-hosted LLM backend.

Any tool that already works with Ollama — Open WebUI, Continue, Cursor,
GitHub Copilot, LangChain, LlamaIndex, the `ollama` Python SDK — connects
with **zero code changes**.

!!! note "PyPI distribution name"
    The package is published on PyPI as **`ollama-proxy-plus`** (the
    `ollama-proxy` name was already taken). Install with
    `pip install ollama-proxy-plus`. The Python import path
    (`ollama_proxy`) and CLI command (`ollama-proxy`) are unchanged.

## How it works

```
Your App  ---->  POST /api/chat            (Ollama protocol)
         ---->  POST /v1/chat/completions  (OpenAI protocol)
                        |
                 ollama-proxy
                        |  routes by model-name prefix
       +----------------+----------------+------- ... -------+
  openai/*        gemini/*        anthropic/*           custom/*
  OpenAI API    Gemini API      Anthropic API     your vLLM / Ray server
```

The **model name prefix** is the only routing key. The proxy speaks **two
wire formats simultaneously**:

- **Ollama protocol** at `/api/*` — Open WebUI, ollama SDK, LangChain Ollama
- **OpenAI protocol** at `/v1/*` — GitHub Copilot, OpenAI SDK, Continue, Cursor

So it works with both ecosystems from a single endpoint.

## Why use it?

- **One proxy, all the providers.** Talk to OpenAI, Anthropic, Gemini, AWS
  Bedrock, Azure, Groq, xAI, Mistral, DeepSeek, Together, Perplexity, Kimi,
  and any OpenAI-compatible server (vLLM, Ray Serve, LM Studio, …) through
  the same client.
- **Centralized API keys.** Clients only know about `localhost:11434`. The
  proxy holds the credentials.
- **Drop-in for Ollama.** Existing Ollama-aware tools work unchanged.
- **Drop-in for OpenAI clients too.** Copilot, Continue, and the OpenAI SDK
  hit the same proxy via the OpenAI wire format.
- **Reliability built in.** Per-provider retry and fallback, structured logs
  with correlation IDs, health endpoints, doctor command.

## Next steps

- [Quick start](quickstart.md) — install and make your first request
- [CLI reference](cli.md) — commands and flags
- [Providers](providers/index.md) — built-in providers and how to add new ones
- [Configuration](config/env.md) — env vars and YAML config
