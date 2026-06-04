# Providers

The proxy has two categories of providers:

1. **OpenAI-compatible providers** — Any provider whose API follows the
   OpenAI chat completions format. These are all handled by a single generic
   adapter. Most providers fall here, including Gemini (via Google's
   OpenAI-compat endpoint). Adding a new one is two lines of config.

2. **Native SDK providers** — Providers with genuinely different wire
   formats: Anthropic, Azure OpenAI, AWS Bedrock.

## Built-in OpenAI-compatible providers

| Prefix | Provider | Auth | Docs |
|--------|----------|------|------|
| `openai/` | OpenAI | `OPENAI_API_KEY` | [details](openai-compat.md) |
| `gemini/` | Google Gemini | `GEMINI_API_KEY` | [details](openai-compat.md) |
| `xai/` | xAI / Grok | `XAI_API_KEY` | [details](openai-compat.md) |
| `groq/` | Groq | `GROQ_API_KEY` | [details](openai-compat.md) |
| `mistral/` | Mistral AI | `MISTRAL_API_KEY` | [details](openai-compat.md) |
| `deepseek/` | DeepSeek | `DEEPSEEK_API_KEY` | [details](openai-compat.md) |
| `together/` | Together AI | `TOGETHER_API_KEY` | [details](openai-compat.md) |
| `perplexity/` | Perplexity | `PERPLEXITY_API_KEY` | [details](openai-compat.md) |
| `kimi/` | Kimi / Moonshot | `KIMI_API_KEY` | [details](openai-compat.md) |

## Built-in native-SDK providers

| Prefix | Provider | Auth | Docs |
|--------|----------|------|------|
| `anthropic/` | Anthropic / Claude | `ANTHROPIC_API_KEY` | [details](anthropic.md) |
| `azure/` | Azure OpenAI | `AZURE_OPENAI_*` vars | [details](azure.md) |
| `bedrock/` | AWS Bedrock | AWS credential chain | [details](bedrock.md) |

## Self-hosted servers

Any OpenAI-compatible REST server works through the same generic adapter:
vLLM, Ray Serve, LM Studio, LocalAI, Llamafile, Hugging Face TGI, Jan, even a
real Ollama instance. See [Self-hosted servers](self-hosted.md).

## Adding a new provider

[Adding a new provider](adding.md) covers:

- Adding an OpenAI-compatible provider via env vars (no code changes)
- Adding via YAML config
- Implementing a custom provider when the wire format is different
