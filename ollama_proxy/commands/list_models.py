"""`ollama-proxy list-models` — print configured models grouped by provider."""

from collections import defaultdict

from ..config import OPENAI_COMPAT_PROVIDERS, PROVIDER_REGISTRY


def run() -> int:
    grouped: dict[str, list[str]] = defaultdict(list)
    for m in PROVIDER_REGISTRY:
        prefix = m.split("/", 1)[0] if "/" in m else "openai"
        grouped[prefix].append(m)

    if not grouped:
        print("No models registered. Add models to PROVIDER_REGISTRY or set EXTRA_MODELS.")
        return 0

    for prefix in sorted(grouped):
        print(f"\n{prefix}/")
        for model in grouped[prefix]:
            print(f"  {model}")

    print("\nConfigured OpenAI-compatible providers:")
    for prefix, cfg in OPENAI_COMPAT_PROVIDERS.items():
        has_key = "✓" if cfg.get("api_key") else "✗"
        print(f"  {has_key} {prefix:15s} {cfg.get('base_url', '')}")
    return 0
