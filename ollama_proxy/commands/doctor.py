"""`ollama-proxy doctor` — sanity-check configuration and provider connectivity."""

import os

import httpx

from ..config import (
    API_KEYS,
    AZURE_CONFIG,
    BEDROCK_CONFIG,
    OPENAI_COMPAT_PROVIDERS,
    PROVIDER_REGISTRY,
)


def _check(name: str, ok: bool, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    print(f"  {mark} {name:30s} {detail}")


def run() -> int:
    print("ollama-proxy doctor")
    print("=" * 50)

    print("\nEnvironment:")
    _check("PROXY_DEBUG", bool(os.getenv("PROXY_DEBUG")), os.getenv("PROXY_DEBUG", "(unset)"))
    _check("EXTRA_MODELS", bool(os.getenv("EXTRA_MODELS")), os.getenv("EXTRA_MODELS", "(unset)") or "(unset)")
    _check("PROXY_CONFIG_FILE", bool(os.getenv("PROXY_CONFIG_FILE")), os.getenv("PROXY_CONFIG_FILE", "(unset)") or "(unset)")

    print("\nNative-SDK providers:")
    _check("anthropic", bool(API_KEYS.get("anthropic")), "key set" if API_KEYS.get("anthropic") else "ANTHROPIC_API_KEY not set")
    _check(
        "azure",
        bool(AZURE_CONFIG.get("api_key") and AZURE_CONFIG.get("endpoint")),
        AZURE_CONFIG.get("endpoint") or "AZURE_OPENAI_* not set",
    )
    _check(
        "bedrock",
        bool(BEDROCK_CONFIG.get("region")),
        f"region={BEDROCK_CONFIG.get('region')}",
    )

    print("\nOpenAI-compatible providers:")
    fail = 0
    for prefix, cfg in OPENAI_COMPAT_PROVIDERS.items():
        if not cfg.get("api_key"):
            _check(prefix, False, "no API key set (skipped connectivity)")
            fail += 1
            continue
        # Try a HEAD/GET on /models — quick auth + connectivity check
        url = cfg["base_url"].rstrip("/") + "/models"
        try:
            r = httpx.get(
                url,
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
                timeout=10,
            )
            if r.status_code == 200:
                _check(prefix, True, f"reachable ({url})")
            elif r.status_code in (401, 403):
                _check(prefix, False, f"auth failed ({r.status_code}) at {url}")
                fail += 1
            else:
                # Some providers don't expose /models; treat non-5xx as ok-ish
                ok = r.status_code < 500
                _check(prefix, ok, f"HTTP {r.status_code} at {url}")
                if not ok:
                    fail += 1
        except httpx.HTTPError as e:
            _check(prefix, False, f"connection failed: {type(e).__name__}")
            fail += 1

    print(f"\nRegistered models: {len(PROVIDER_REGISTRY)}")
    return 0 if fail == 0 else 1
