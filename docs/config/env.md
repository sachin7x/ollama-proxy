# Environment variables

The proxy reads configuration from environment variables. A `.env` file at
the working directory is auto-loaded via `python-dotenv`.

See [`.env.example`](https://github.com/skamalj/ollama-proxy/blob/master/.env.example)
in the repo for a starter template.

## Provider API keys

Set keys for the providers you actually use — others can stay unset.

| Variable | Provider |
|----------|----------|
| `OPENAI_API_KEY` | OpenAI |
| `GEMINI_API_KEY` | Google Gemini |
| `ANTHROPIC_API_KEY` | Anthropic / Claude |
| `XAI_API_KEY` | xAI / Grok |
| `GROQ_API_KEY` | Groq |
| `MISTRAL_API_KEY` | Mistral AI |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `TOGETHER_API_KEY` | Together AI |
| `PERPLEXITY_API_KEY` | Perplexity |
| `KIMI_API_KEY` | Kimi / Moonshot |

## Azure OpenAI

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_API_KEY` | API key |
| `AZURE_OPENAI_ENDPOINT` | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_API_VERSION` | e.g. `2024-08-01-preview` |

## AWS Bedrock

Bedrock uses the standard AWS credential chain (no API key):

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Explicit credentials |
| `AWS_REGION` / `AWS_DEFAULT_REGION` | AWS region (default `us-east-1`) |
| `AWS_PROFILE` | Use a named profile from `~/.aws/credentials` |

Or run on EC2/ECS/Lambda with an attached IAM role and `boto3` picks it up
automatically.

## Behavior toggles

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_DEBUG` | `0` | `1` enables verbose request/response logging |
| `PROXY_LOG_JSON` | `0` | `1` enables JSON-formatted logs |
| `PROXY_HOST` | `0.0.0.0` | Bind host (CLI flag overrides) |
| `PROXY_PORT` | `11434` | Bind port (CLI flag overrides) |
| `PROXY_CONFIG_FILE` | – | Path to YAML config file |
| `EXTRA_MODELS` | – | Comma-separated `prefix/model` list |

## Auto-registering OpenAI-compatible providers

Set both an API key and a base URL for any custom provider:

```bash
export PROVIDERS_VLLM_API_KEY=EMPTY
export PROVIDERS_VLLM_BASE_URL=http://localhost:8000/v1
```

The lowercased name (`vllm`) becomes the routing prefix. See
[Adding a new provider](../providers/adding.md).

## Example `.env`

```bash
# Cloud providers
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...

# Local vLLM server (auto-discovered)
PROVIDERS_VLLM_API_KEY=EMPTY
PROVIDERS_VLLM_BASE_URL=http://localhost:8000/v1

# Behavior
PROXY_DEBUG=0
EXTRA_MODELS=openai/gpt-5,gemini/gemini-3-pro
```
