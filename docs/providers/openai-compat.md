# OpenAI-compatible providers

A single adapter (`OpenAICompatProvider`) handles every provider whose API
follows the OpenAI chat completions format. Adding a new one is two lines of
configuration — no code changes.

!!! warning "Endpoints can change"
    The base URLs below were correct at the time of writing. Always verify
    against each provider's official documentation before relying on them
    in production.

## Built-in providers

| Prefix | Provider | Base URL | Env Variable | Docs |
|--------|----------|----------|--------------|------|
| `openai/` | OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/docs) |
| `gemini/` | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY` | [ai.google.dev](https://ai.google.dev/gemini-api/docs) |
| `xai/` | xAI / Grok | `https://api.x.ai/v1` | `XAI_API_KEY` | [console.x.ai](https://console.x.ai) |
| `groq/` | Groq | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `mistral/` | Mistral AI | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | [docs.mistral.ai](https://docs.mistral.ai) |
| `deepseek/` | DeepSeek | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | [platform.deepseek.com](https://platform.deepseek.com) |
| `together/` | Together AI | `https://api.together.xyz/v1` | `TOGETHER_API_KEY` | [docs.together.ai](https://docs.together.ai) |
| `perplexity/` | Perplexity | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | [docs.perplexity.ai](https://docs.perplexity.ai) |
| `kimi/` | Kimi / Moonshot | `https://api.moonshot.ai/v1` | `KIMI_API_KEY` | [platform.kimi.ai](https://platform.kimi.ai/docs) |

## Capabilities

All OpenAI-compatible providers automatically support:

- **Streaming** (Ollama and OpenAI formats)
- **Tool calls** — passed through with proper `finish_reason`
- **JSON mode** / **JSON schema** — via `response_format` (OpenAI) or
  `format` (Ollama)
- **Embeddings** — via `/api/embed` and `/api/embeddings`
- **Stop sequences**, **temperature**, **top_p**, **max_tokens**

## Provider-specific notes

### Kimi / Moonshot

Kimi K2.5+ models support a `thinking` mode that produces reasoning tokens
before the final answer. The proxy automatically disables this on the
`/v1/chat/completions` endpoint (Copilot can't render reasoning tokens). Set
manually via `extra_body` if you want it back.

Kimi K2.5+ also requires `temperature=1`. The proxy avoids passing
`temperature` from the OpenAI-compat endpoint so client defaults don't
trip this.

### Gemini

Gemini routes through Google's [OpenAI-compatible endpoint](https://ai.google.dev/gemini-api/docs/openai),
not the native `google-generativeai` SDK. This gives you tool calls,
streaming, and structured output for free with no SDK installation.

### Self-hosted

Most local LLM servers (vLLM, Ray Serve, LM Studio, LocalAI, Llamafile, Jan,
Hugging Face TGI, even a real Ollama instance) speak the OpenAI-compatible
wire format. See [Self-hosted servers](self-hosted.md).
