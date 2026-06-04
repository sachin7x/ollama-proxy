"""
config.py - API keys and model registry
Set keys via environment variables or paste them here for local dev.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging / tracing (set PROXY_DEBUG=1 to enable request/response logging)
# ---------------------------------------------------------------------------
DEBUG_LOGGING = os.getenv("PROXY_DEBUG", "0").lower() in ("1", "true", "yes", "on")

# ---------------------------------------------------------------------------
# Standard provider keys (only for providers with non-OpenAI-compatible SDKs)
# ---------------------------------------------------------------------------
API_KEYS = {
    "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
}

# ---------------------------------------------------------------------------
# Azure OpenAI - needs endpoint + api_version alongside the key.
# The "model" field maps to the Azure DEPLOYMENT NAME.
# ---------------------------------------------------------------------------
AZURE_CONFIG = {
    "api_key":     os.getenv("AZURE_OPENAI_API_KEY", ""),
    "endpoint":    os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
}

# Optional per-deployment overrides. Key = deployment name in Azure AI Studio.
# Deployments not listed here fall back to AZURE_CONFIG above.
# Example:
# AZURE_DEPLOYMENTS = {
#     "gpt4o-prod": {"api_key": "...", "endpoint": "https://prod.openai.azure.com/", "api_version": "2024-08-01-preview"},
#     "gpt35-dev":  {"api_key": "...", "endpoint": "https://dev.openai.azure.com/",  "api_version": "2024-02-01"},
# }
AZURE_DEPLOYMENTS: dict = {}

# ---------------------------------------------------------------------------
# AWS Bedrock - uses boto3 Converse API with standard AWS credential chain.
# Auth: AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, ~/.aws/credentials, or IAM role.
# ---------------------------------------------------------------------------
BEDROCK_CONFIG = {
    "region":  os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
    "profile": os.getenv("AWS_PROFILE", None),  # optional — uses default credential chain
}

# ---------------------------------------------------------------------------
# OpenAI-compatible providers (share the same SDK, different base_url + key)
# ---------------------------------------------------------------------------
OPENAI_COMPAT_PROVIDERS = {
    "openai": {
        "api_key":  os.getenv("OPENAI_API_KEY", ""),
        "base_url": "https://api.openai.com/v1",
    },
    "gemini": {
        "api_key":  os.getenv("GEMINI_API_KEY", ""),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    "kimi": {
        "api_key":  os.getenv("KIMI_API_KEY", ""),
        "base_url": "https://api.moonshot.ai/v1",
    },
    "xai": {
        "api_key":  os.getenv("XAI_API_KEY", ""),
        "base_url": "https://api.x.ai/v1",
    },
    "groq": {
        "api_key":  os.getenv("GROQ_API_KEY", ""),
        "base_url": "https://api.groq.com/openai/v1",
    },
    "mistral": {
        "api_key":  os.getenv("MISTRAL_API_KEY", ""),
        "base_url": "https://api.mistral.ai/v1",
    },
    "deepseek": {
        "api_key":  os.getenv("DEEPSEEK_API_KEY", ""),
        "base_url": "https://api.deepseek.com",
    },
    "together": {
        "api_key":  os.getenv("TOGETHER_API_KEY", ""),
        "base_url": "https://api.together.xyz/v1",
    },
    "perplexity": {
        "api_key":  os.getenv("PERPLEXITY_API_KEY", ""),
        "base_url": "https://api.perplexity.ai",
    },
}

# ---------------------------------------------------------------------------
# Model registry - everything in GET /api/tags
# Add or remove entries freely - no other file needs changing.
# ---------------------------------------------------------------------------
PROVIDER_REGISTRY = [
    # OpenAI
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4-turbo",
    "openai/o1-mini",
    # xAI / Grok
    "xai/grok-2",
    "xai/grok-2-mini",
    "xai/grok-beta",
    # Groq (fast inference)
    "groq/llama-3.3-70b-versatile",
    "groq/llama-3.1-8b-instant",
    "groq/mixtral-8x7b-32768",
    "groq/gemma2-9b-it",
    # Mistral AI
    "mistral/mistral-large-latest",
    "mistral/mistral-small-latest",
    "mistral/codestral-latest",
    "mistral/mistral-embed",
    # DeepSeek
    "deepseek/deepseek-chat",
    "deepseek/deepseek-reasoner",
    # Together AI
    "together/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "together/Qwen/Qwen2.5-72B-Instruct-Turbo",
    "together/deepseek-ai/DeepSeek-R1",
    # Perplexity
    "perplexity/sonar",
    "perplexity/sonar-pro",
    "perplexity/sonar-reasoning",
    # Gemini
    "gemini/gemini-2.5-pro",
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.5-flash-lite",
    "gemini/gemini-2.0-flash",
    "gemini/gemini-1.5-pro",
    "gemini/gemini-1.5-flash",
    # Anthropic / Claude
    "anthropic/claude-3-5-sonnet-20241022",
    "anthropic/claude-haiku-4-5",
    "anthropic/claude-sonnet-4-5",
    "anthropic/claude-opus-4-5",
    # Kimi (Moonshot AI)
    "kimi/kimi-k2.6",
    "kimi/kimi-k2.5",
    "kimi/moonshot-v1-8k",
    "kimi/moonshot-v1-32k",
    "kimi/moonshot-v1-128k",
    # Azure OpenAI - uncomment and add your deployment names
    # "azure/my-gpt4o-deployment",
    # "azure/my-gpt35-deployment",
    # AWS Bedrock - uncomment and use your model/inference-profile IDs
    # "bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0",
    # "bedrock/us.amazon.nova-pro-v1:0",
    # "bedrock/us.amazon.nova-lite-v1:0",
    # "bedrock/us.meta.llama3-1-70b-instruct-v1:0",
]

# ---------------------------------------------------------------------------
# Extra models from environment - quick way to add models without editing this file.
# Set EXTRA_MODELS as a comma-separated list, e.g.:
#   EXTRA_MODELS="openai/gpt-4o-2025,gemini/gemini-2.5-pro-preview,kimi/kimi-k2.6"
# ---------------------------------------------------------------------------
_extra = os.getenv("EXTRA_MODELS", "").strip()
if _extra:
    PROVIDER_REGISTRY.extend(
        m.strip() for m in _extra.split(",") if m.strip() and m.strip() not in PROVIDER_REGISTRY
    )
