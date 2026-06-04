"""
config.py - configuration loading for ollama-proxy.

Sources, in order of precedence (later wins):
1. Hardcoded defaults
2. Built-in known providers (env-var driven)
3. Auto-discovered providers from PROVIDERS_<NAME>_API_KEY / PROVIDERS_<NAME>_BASE_URL
4. YAML config file at $PROXY_CONFIG_FILE (or ./ollama-proxy.yaml)
5. EXTRA_MODELS env var (model list only)
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging / tracing
# ---------------------------------------------------------------------------
DEBUG_LOGGING = os.getenv("PROXY_DEBUG", "0").lower() in ("1", "true", "yes", "on")
JSON_LOGGING = os.getenv("PROXY_LOG_JSON", "0").lower() in ("1", "true", "yes", "on")

# ---------------------------------------------------------------------------
# Native-SDK provider config
# ---------------------------------------------------------------------------
API_KEYS = {
    "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
}

AZURE_CONFIG = {
    "api_key":     os.getenv("AZURE_OPENAI_API_KEY", ""),
    "endpoint":    os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
}

AZURE_DEPLOYMENTS: dict = {}

BEDROCK_CONFIG = {
    "region":  os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
    "profile": os.getenv("AWS_PROFILE", None),
}

# ---------------------------------------------------------------------------
# OpenAI-compatible providers — built-in known list
# ---------------------------------------------------------------------------
OPENAI_COMPAT_PROVIDERS: dict[str, dict[str, str]] = {
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
# Per-provider settings (retries, fallback) — populated from config file
# ---------------------------------------------------------------------------
PROVIDER_SETTINGS: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Default model registry — minimal, well-known models.
# Users override via PROVIDER_REGISTRY in config file or EXTRA_MODELS env var.
# ---------------------------------------------------------------------------
PROVIDER_REGISTRY: list[str] = [
    # OpenAI
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4-turbo",
    "openai/o1-mini",
    # Gemini
    "gemini/gemini-2.5-pro",
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.5-flash-lite",
    "gemini/gemini-2.0-flash",
    "gemini/gemini-1.5-pro",
    "gemini/gemini-1.5-flash",
    # Anthropic
    "anthropic/claude-3-5-sonnet-20241022",
    "anthropic/claude-haiku-4-5",
    "anthropic/claude-sonnet-4-5",
    "anthropic/claude-opus-4-5",
    # xAI / Grok
    "xai/grok-2",
    "xai/grok-2-mini",
    "xai/grok-beta",
    # Groq
    "groq/llama-3.3-70b-versatile",
    "groq/llama-3.1-8b-instant",
    "groq/mixtral-8x7b-32768",
    "groq/gemma2-9b-it",
    # Mistral
    "mistral/mistral-large-latest",
    "mistral/mistral-small-latest",
    "mistral/codestral-latest",
    "mistral/mistral-embed",
    # DeepSeek
    "deepseek/deepseek-chat",
    "deepseek/deepseek-reasoner",
    # Together
    "together/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "together/Qwen/Qwen2.5-72B-Instruct-Turbo",
    "together/deepseek-ai/DeepSeek-R1",
    # Perplexity
    "perplexity/sonar",
    "perplexity/sonar-pro",
    "perplexity/sonar-reasoning",
    # Kimi
    "kimi/kimi-k2.6",
    "kimi/kimi-k2.5",
    "kimi/moonshot-v1-8k",
    "kimi/moonshot-v1-32k",
    "kimi/moonshot-v1-128k",
]


# ---------------------------------------------------------------------------
# Auto-discover OpenAI-compat providers from environment
# Format: PROVIDERS_<NAME>_API_KEY and PROVIDERS_<NAME>_BASE_URL
#   e.g. PROVIDERS_VLLM_API_KEY=EMPTY  PROVIDERS_VLLM_BASE_URL=http://...
# Lowercase prefix becomes the routing key (e.g. vllm/<model>).
# ---------------------------------------------------------------------------
def _discover_env_providers() -> None:
    """Scan env vars for PROVIDERS_<NAME>_* and register them."""
    discovered: dict[str, dict[str, str]] = {}
    for key, value in os.environ.items():
        if not key.startswith("PROVIDERS_"):
            continue
        rest = key[len("PROVIDERS_"):]
        if "_" not in rest:
            continue
        # Split on last "_" to support BASE_URL (which contains underscore)
        if rest.endswith("_API_KEY"):
            name = rest[:-len("_API_KEY")].lower()
            discovered.setdefault(name, {})["api_key"] = value
        elif rest.endswith("_BASE_URL"):
            name = rest[:-len("_BASE_URL")].lower()
            discovered.setdefault(name, {})["base_url"] = value

    for name, cfg in discovered.items():
        if "base_url" not in cfg:
            continue  # need at least a base_url
        cfg.setdefault("api_key", "EMPTY")  # local servers often use any non-empty value
        OPENAI_COMPAT_PROVIDERS[name] = cfg


_discover_env_providers()


# ---------------------------------------------------------------------------
# YAML config file loader (optional)
# Looks for $PROXY_CONFIG_FILE, then ./ollama-proxy.yaml, then ./ollama-proxy.yml
# ---------------------------------------------------------------------------
def _load_yaml_config() -> None:
    path_str = os.getenv("PROXY_CONFIG_FILE")
    candidates: list[Path] = []
    if path_str:
        candidates.append(Path(path_str))
    candidates += [Path("ollama-proxy.yaml"), Path("ollama-proxy.yml")]

    for p in candidates:
        if p.exists():
            break
    else:
        return

    try:
        import yaml
    except ImportError:
        # PyYAML is optional; skip silently if not installed
        return

    with open(p) as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        return

    # providers: { name: { api_key, base_url, retries?, fallback? }, ... }
    for name, cfg in (data.get("providers") or {}).items():
        if not isinstance(cfg, dict):
            continue
        if "base_url" in cfg or "api_key" in cfg:
            entry = OPENAI_COMPAT_PROVIDERS.setdefault(name.lower(), {})
            if "api_key" in cfg:
                entry["api_key"] = _expand(cfg["api_key"])
            if "base_url" in cfg:
                entry["base_url"] = _expand(cfg["base_url"])
        # Per-provider settings (retries, fallback)
        settings: dict[str, Any] = {}
        if "retries" in cfg:
            settings["retries"] = int(cfg["retries"])
        if "fallback" in cfg:
            settings["fallback"] = str(cfg["fallback"])
        if settings:
            PROVIDER_SETTINGS[name.lower()] = settings

    # models: [ "openai/gpt-5", ... ]  — replaces or extends the registry
    models = data.get("models")
    if isinstance(models, list):
        for m in models:
            if isinstance(m, str) and m not in PROVIDER_REGISTRY:
                PROVIDER_REGISTRY.append(m)


def _expand(value: Any) -> str:
    """Expand ${ENV_VAR} references in YAML strings."""
    if not isinstance(value, str):
        return value
    return os.path.expandvars(value)


_load_yaml_config()


# ---------------------------------------------------------------------------
# Apply EXTRA_MODELS env var (highest precedence, comma-separated)
# ---------------------------------------------------------------------------
_extra = os.getenv("EXTRA_MODELS", "").strip()
if _extra:
    for m in (s.strip() for s in _extra.split(",") if s.strip()):
        if m not in PROVIDER_REGISTRY:
            PROVIDER_REGISTRY.append(m)
