# Anthropic / Claude

Uses the official `anthropic` Python SDK (Anthropic's wire format isn't
OpenAI-compatible, so it gets a dedicated adapter).

## Install

```bash
pip install "ollama-proxy-plus[anthropic]"
```

## Configure

Set:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Use

Prefix: `anthropic/`. The model ID after the prefix is the Anthropic API model
ID:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "anthropic/claude-sonnet-4-5",
  "messages": [{"role": "user", "content": "Hello!"}]
}'
```

The `claude/` prefix is also accepted as an alias.

## Default models in the registry

```
anthropic/claude-3-5-sonnet-20241022
anthropic/claude-haiku-4-5
anthropic/claude-sonnet-4-5
anthropic/claude-opus-4-5
```

Add others via [`EXTRA_MODELS`](../config/models.md) or YAML config.

## Implementation notes

- System messages are extracted from the messages array and passed as
  Anthropic's top-level `system` parameter.
- `max_tokens` defaults to 4096 if not specified (Anthropic requires it).
- Roles are limited to `user` and `assistant` in the messages array
  (the proxy handles the conversion automatically).
