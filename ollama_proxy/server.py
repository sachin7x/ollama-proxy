"""
ollama-proxy — speak the Ollama API protocol on port 11434, route to cloud LLMs.

Wire formats served simultaneously:
  /api/*          Ollama protocol  (Open WebUI, ollama SDK, LangChain Ollama)
  /v1/*           OpenAI protocol  (Copilot, Continue, Cursor, OpenAI SDK)

Optional env vars:
  PROXY_DEBUG=1                     verbose request/response logging
  PROXY_LOG_JSON=1                  JSON-formatted logs
  PROXY_CONFIG_FILE=path.yaml       YAML config (providers + models)
  EXTRA_MODELS=p1/m1,p2/m2          add models to /api/tags
  PROVIDERS_<NAME>_API_KEY=...      auto-register an OpenAI-compat provider
  PROVIDERS_<NAME>_BASE_URL=...
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from . import __version__
from .config import (
    API_KEYS,
    AZURE_CONFIG,
    AZURE_DEPLOYMENTS,
    BEDROCK_CONFIG,
    DEBUG_LOGGING,
    JSON_LOGGING,
    OPENAI_COMPAT_PROVIDERS,
    PROVIDER_REGISTRY,
    PROVIDER_SETTINGS,
)
from .logging_config import configure_logging, new_request_id, request_id_ctx
from .providers.anthropic_provider import AnthropicProvider
from .providers.azure_provider import AzureProvider
from .providers.bedrock_provider import BedrockProvider
from .providers.openai_compat_provider import OpenAICompatProvider
from .retry import with_retry_and_fallback

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = configure_logging(debug=DEBUG_LOGGING, json_format=JSON_LOGGING)


app = FastAPI(title="ollama-proxy", version=__version__)


# ---------------------------------------------------------------------------
# Request-ID middleware (correlation IDs for structured logging)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or new_request_id()
    token = request_id_ctx.set(rid)
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        request_id_ctx.reset(token)
    response.headers["x-request-id"] = rid
    if DEBUG_LOGGING:
        logger.debug(
            f"{request.method} {request.url.path} "
            f"-> {response.status_code} ({elapsed_ms:.1f}ms)"
        )
    return response


# ---------------------------------------------------------------------------
# Provider routing
# ---------------------------------------------------------------------------
def get_provider(model: str):
    """Parse 'provider/model-id' and return a provider instance."""
    if "/" in model:
        prefix, model_id = model.split("/", 1)
    else:
        prefix, model_id = "openai", model
    prefix = prefix.lower()

    if prefix in ("anthropic", "claude"):
        return AnthropicProvider(api_key=API_KEYS["anthropic"], model=model_id)
    if prefix == "azure":
        cfg = AZURE_DEPLOYMENTS.get(model_id, AZURE_CONFIG)
        return AzureProvider(
            api_key=cfg["api_key"],
            model=model_id,
            endpoint=cfg["endpoint"],
            api_version=cfg["api_version"],
        )
    if prefix == "bedrock":
        return BedrockProvider(
            model=model_id,
            region=BEDROCK_CONFIG["region"],
            profile=BEDROCK_CONFIG["profile"],
        )
    if prefix in OPENAI_COMPAT_PROVIDERS:
        cfg = OPENAI_COMPAT_PROVIDERS[prefix]
        return OpenAICompatProvider(
            api_key=cfg["api_key"],
            model=model_id,
            base_url=cfg["base_url"],
        )

    supported = ", ".join(
        ["anthropic", "azure", "bedrock"] + sorted(OPENAI_COMPAT_PROVIDERS.keys())
    )
    raise ValueError(f"Unknown provider prefix: '{prefix}'. Supported: {supported}")


def _provider_call_factory(model: str, op: str, *args, **kwargs):
    """Return a no-arg coroutine factory that calls the provider's `op` method
    on the model. Used by retry/fallback to construct the fallback call."""

    def factory(target_model: str):
        async def call():
            provider = get_provider(target_model)
            method = getattr(provider, op)
            return await method(*args, **kwargs)

        return call

    # When called for the primary, wrap as no-arg
    return factory


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
def _log_request(endpoint: str, body: dict) -> None:
    if not DEBUG_LOGGING:
        return
    msgs = body.get("messages", []) or []
    tools = body.get("tools", []) or []
    logger.debug(
        f"REQ {endpoint} model={body.get('model', '?')} "
        f"stream={body.get('stream', '?')} messages={len(msgs)} "
        f"tools={len(tools)} format={body.get('format')}"
    )


def _log_response(endpoint: str, status: int, detail: str = "") -> None:
    if not DEBUG_LOGGING:
        return
    logger.debug(f"RES {endpoint} status={status} {detail}")


# ---------------------------------------------------------------------------
# Health / version / root
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Real Ollama returns plain text — some clients check for this exact string."""
    return PlainTextResponse("Ollama is running")


@app.get("/api/version")
async def version():
    # Some clients require >= 0.6.4
    return {"version": "0.6.5"}


@app.get("/health")
async def health():
    """Lightweight health check — does not hit upstream providers."""
    return {
        "status": "ok",
        "version": __version__,
        "providers": {
            "openai_compat": list(OPENAI_COMPAT_PROVIDERS.keys()),
            "anthropic": bool(API_KEYS.get("anthropic")),
            "azure": bool(AZURE_CONFIG.get("api_key") and AZURE_CONFIG.get("endpoint")),
            "bedrock": bool(BEDROCK_CONFIG.get("region")),
        },
        "models_registered": len(PROVIDER_REGISTRY),
    }


@app.get("/health/providers")
async def health_providers():
    """Connectivity check — pings each OpenAI-compat provider's /models endpoint."""
    results: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for prefix, cfg in OPENAI_COMPAT_PROVIDERS.items():
            if not cfg.get("api_key"):
                results[prefix] = {"status": "unconfigured", "detail": "no API key"}
                continue
            url = cfg["base_url"].rstrip("/") + "/models"
            try:
                r = await client.get(
                    url, headers={"Authorization": f"Bearer {cfg['api_key']}"}
                )
                results[prefix] = {
                    "status": "ok" if r.status_code < 400 else "error",
                    "http_status": r.status_code,
                    "url": url,
                }
            except httpx.HTTPError as e:
                results[prefix] = {
                    "status": "unreachable",
                    "detail": f"{type(e).__name__}: {e}",
                    "url": url,
                }
    overall = (
        "ok"
        if all(v.get("status") == "ok" for v in results.values())
        else "degraded"
    )
    return {"overall": overall, "providers": results}


# ---------------------------------------------------------------------------
# Model listing
# ---------------------------------------------------------------------------
@app.get("/api/tags")
async def list_models():
    """List all available models from PROVIDER_REGISTRY."""
    models = []
    for name in PROVIDER_REGISTRY:
        family = name.split("/")[0] if "/" in name else "openai"
        models.append({
            "name": name,
            "model": name,
            "modified_at": "2025-01-01T00:00:00Z",
            "size": 0,
            "digest": f"sha256:{abs(hash(name)):064x}"[:71],
            "details": {
                "parent_model": "",
                "format": "cloud",
                "family": family,
                "families": [family],
                "parameter_size": "cloud",
                "quantization_level": "none",
            },
        })
    return {"models": models}


@app.get("/api/ps")
async def list_running():
    return {"models": []}


@app.post("/api/show")
async def show_model(request: Request):
    """Show model info. Accepts any 'prefix/model' if the prefix is configured."""
    body = await request.json()
    model = body.get("model", "")

    prefix = model.split("/", 1)[0].lower() if "/" in model else "openai"
    known_prefixes = (
        {"anthropic", "claude", "azure", "bedrock"}
        | set(OPENAI_COMPAT_PROVIDERS.keys())
    )
    if prefix not in known_prefixes and model not in PROVIDER_REGISTRY:
        return JSONResponse(
            status_code=404, content={"error": f"model '{model}' not found"}
        )

    family = model.split("/")[0] if "/" in model else "openai"
    return {
        "model": model,
        "modelfile": f"# Modelfile for {model}\nFROM {model}\n",
        "parameters": "temperature 0.8\nstop \"<|end|>\"",
        "template": "{{ .System }}\n{{ .Prompt }}",
        "details": {
            "parent_model": "",
            "format": "cloud",
            "family": family,
            "families": [family],
            "parameter_size": "cloud",
            "quantization_level": "none",
        },
        "model_info": {
            "general.architecture": family,
            "general.basename": model,
        },
        "capabilities": ["completion", "tools"],
    }


# ---------------------------------------------------------------------------
# Model management — mocked for cloud proxy
# ---------------------------------------------------------------------------
@app.post("/api/pull")
async def pull_model(request: Request):
    body = await request.json()
    model = body.get("model", "unknown")
    stream = body.get("stream", True)

    async def _pull_stream():
        yield json.dumps({"status": f"pulling manifest for {model}"}) + "\n"
        yield json.dumps({"status": "verifying sha256 digest"}) + "\n"
        yield json.dumps({"status": "success"}) + "\n"

    if stream:
        return StreamingResponse(_pull_stream(), media_type="application/x-ndjson")
    return {"status": "success"}


@app.delete("/api/delete")
async def delete_model(request: Request):
    return JSONResponse(status_code=200, content={})


@app.post("/api/copy")
async def copy_model(request: Request):
    return JSONResponse(status_code=200, content={})


@app.post("/api/push")
async def push_model(request: Request):
    return JSONResponse(
        status_code=501,
        content={"error": "push is not supported by this cloud proxy"},
    )


@app.post("/api/create")
async def create_model(request: Request):
    return JSONResponse(
        status_code=501,
        content={"error": "create is not supported by this cloud proxy"},
    )


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
@app.post("/api/embeddings")
async def embeddings_legacy(request: Request):
    body = await request.json()
    model = body.get("model", "openai/text-embedding-3-small")
    prompt = body.get("prompt", "")

    try:
        provider = get_provider(model)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    try:
        embedding = await provider.embed(prompt)
    except NotImplementedError:
        return JSONResponse(
            status_code=400,
            content={"error": f"Provider '{model.split('/')[0]}' does not support embeddings."},
        )
    return {"embedding": embedding}


@app.post("/api/embed")
async def embeddings_new(request: Request):
    body = await request.json()
    model = body.get("model", "openai/text-embedding-3-small")
    input_data = body.get("input", "")
    inputs = [input_data] if isinstance(input_data, str) else input_data

    try:
        provider = get_provider(model)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    try:
        embeddings = [await provider.embed(text) for text in inputs]
    except NotImplementedError:
        return JSONResponse(
            status_code=400,
            content={"error": f"Provider '{model.split('/')[0]}' does not support embeddings."},
        )
    return {
        "model": model,
        "embeddings": embeddings,
        "total_duration": 0,
        "load_duration": 0,
        "prompt_eval_count": sum(len(t.split()) for t in inputs),
    }


# ---------------------------------------------------------------------------
# Generation (Ollama protocol)
# ---------------------------------------------------------------------------
@app.post("/api/generate")
async def generate(request: Request):
    body = await request.json()
    model = body.get("model", "openai/gpt-4o-mini")
    prompt = body.get("prompt", "")
    system = body.get("system", "")
    stream = body.get("stream", True)
    options = body.get("options", {})
    fmt = body.get("format")

    _log_request("/api/generate", body)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    if fmt:
        options["_format"] = fmt

    try:
        provider = get_provider(model)
    except ValueError as e:
        _log_response("/api/generate", 400, str(e))
        return JSONResponse(status_code=400, content={"error": str(e)})

    if stream:
        return StreamingResponse(
            _stream_generate(provider, model, messages, options),
            media_type="application/x-ndjson",
        )

    try:
        async def _primary():
            return await provider.chat(messages, stream=False, options=options)

        def _fb_factory(target: str):
            async def call():
                p = get_provider(target)
                return await p.chat(messages, stream=False, options=options)
            return call

        t0 = _now_ns()
        content = await with_retry_and_fallback(
            model, _primary, settings=PROVIDER_SETTINGS, fallback_call_factory=_fb_factory
        )
        duration = _now_ns() - t0
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})

    return {
        "model": model,
        "created_at": _iso_now(),
        "response": content,
        "done": True,
        "done_reason": "stop",
        "context": [],
        "total_duration": duration,
        "load_duration": 0,
        "prompt_eval_count": len(prompt.split()),
        "prompt_eval_duration": 0,
        "eval_count": len(content.split()),
        "eval_duration": duration,
    }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    model = body.get("model", "openai/gpt-4o-mini")
    messages = body.get("messages", [])
    stream = body.get("stream", True)
    options = body.get("options", {})
    tools = body.get("tools")
    fmt = body.get("format")

    _log_request("/api/chat", body)

    try:
        provider = get_provider(model)
    except ValueError as e:
        _log_response("/api/chat", 400, str(e))
        return JSONResponse(status_code=400, content={"error": str(e)})

    if tools:
        options["_tools"] = tools
    if fmt:
        options["_format"] = fmt

    if stream:
        return StreamingResponse(
            _stream_chat(provider, model, messages, options),
            media_type="application/x-ndjson",
        )

    try:
        async def _primary():
            return await provider.chat(messages, stream=False, options=options)

        def _fb_factory(target: str):
            async def call():
                p = get_provider(target)
                return await p.chat(messages, stream=False, options=options)
            return call

        t0 = _now_ns()
        content = await with_retry_and_fallback(
            model, _primary, settings=PROVIDER_SETTINGS, fallback_call_factory=_fb_factory
        )
        duration = _now_ns() - t0
    except Exception as e:
        _log_response("/api/chat", 502, str(e))
        return JSONResponse(status_code=502, content={"error": str(e)})

    _log_response("/api/chat", 200, f"tokens={len(content.split())}")
    return {
        "model": model,
        "created_at": _iso_now(),
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        "total_duration": duration,
        "load_duration": 0,
        "prompt_eval_count": sum(len(m.get("content", "").split()) for m in messages),
        "prompt_eval_duration": 0,
        "eval_count": len(content.split()),
        "eval_duration": duration,
    }


# ---------------------------------------------------------------------------
# Streaming helpers (Ollama protocol)
# ---------------------------------------------------------------------------
async def _stream_chat(provider, model: str, messages: list, options: dict) -> AsyncIterator[str]:
    t0 = _now_ns()
    eval_count = 0
    try:
        async for chunk in provider.chat_stream(messages, options=options):
            eval_count += len(chunk.split())
            yield json.dumps({
                "model": model,
                "created_at": _iso_now(),
                "message": {"role": "assistant", "content": chunk},
                "done": False,
            }) + "\n"
    except Exception as e:
        yield json.dumps({
            "model": model,
            "created_at": _iso_now(),
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "error",
            "error": str(e),
        }) + "\n"
        return

    yield json.dumps({
        "model": model,
        "created_at": _iso_now(),
        "message": {"role": "assistant", "content": ""},
        "done": True,
        "done_reason": "stop",
        "total_duration": _now_ns() - t0,
        "load_duration": 0,
        "prompt_eval_count": sum(len(m.get("content", "").split()) for m in messages),
        "prompt_eval_duration": 0,
        "eval_count": eval_count,
        "eval_duration": _now_ns() - t0,
    }) + "\n"


async def _stream_generate(provider, model: str, messages: list, options: dict) -> AsyncIterator[str]:
    t0 = _now_ns()
    eval_count = 0
    try:
        async for chunk in provider.chat_stream(messages, options=options):
            eval_count += len(chunk.split())
            yield json.dumps({
                "model": model,
                "created_at": _iso_now(),
                "response": chunk,
                "done": False,
            }) + "\n"
    except Exception as e:
        yield json.dumps({
            "model": model,
            "created_at": _iso_now(),
            "response": "",
            "done": True,
            "done_reason": "error",
            "error": str(e),
        }) + "\n"
        return

    yield json.dumps({
        "model": model,
        "created_at": _iso_now(),
        "response": "",
        "done": True,
        "done_reason": "stop",
        "context": [],
        "total_duration": _now_ns() - t0,
        "load_duration": 0,
        "prompt_eval_count": sum(len(m.get("content", "").split()) for m in messages),
        "prompt_eval_duration": 0,
        "eval_count": eval_count,
        "eval_duration": _now_ns() - t0,
    }) + "\n"


# ---------------------------------------------------------------------------
# OpenAI-compatible endpoints (for Copilot, Continue, Cursor, OpenAI SDK)
# ---------------------------------------------------------------------------
@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "openai/gpt-4o-mini")
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    tools = body.get("tools")

    _log_request("/v1/chat/completions", body)

    options: dict[str, Any] = {}
    if "max_tokens" in body:
        options["max_tokens"] = body["max_tokens"]
    if "max_completion_tokens" in body:
        options["max_tokens"] = body["max_completion_tokens"]
    if "stop" in body:
        options["stop"] = body["stop"]
    if tools:
        options["_tools"] = tools
    if "response_format" in body:
        options["_response_format"] = body["response_format"]

    try:
        provider = get_provider(model)
    except ValueError as e:
        _log_response("/v1/chat/completions", 400, str(e))
        return JSONResponse(
            status_code=400,
            content={"error": {"message": str(e), "type": "invalid_request_error"}},
        )

    # Disable thinking for Kimi k2 family on the OpenAI-compat endpoint
    extra_body: dict[str, Any] = {}
    prefix = model.split("/")[0].lower() if "/" in model else ""
    if prefix == "kimi":
        extra_body["thinking"] = {"type": "disabled"}
    if extra_body:
        options["_extra_body"] = extra_body

    if stream:
        return StreamingResponse(
            _stream_openai_chat(provider, model, messages, options),
            media_type="text/event-stream",
        )

    try:
        async def _primary():
            chat_full = getattr(provider, "chat_full", None)
            if chat_full:
                return await chat_full(messages, options=options)
            content = await provider.chat(messages, stream=False, options=options)
            return {"role": "assistant", "content": content, "finish_reason": "stop"}

        def _fb_factory(target: str):
            async def call():
                p = get_provider(target)
                chat_full = getattr(p, "chat_full", None)
                if chat_full:
                    return await chat_full(messages, options=options)
                content = await p.chat(messages, stream=False, options=options)
                return {"role": "assistant", "content": content, "finish_reason": "stop"}
            return call

        full = await with_retry_and_fallback(
            model, _primary, settings=PROVIDER_SETTINGS, fallback_call_factory=_fb_factory
        )
    except Exception as e:
        _log_response("/v1/chat/completions", 502, str(e))
        return JSONResponse(
            status_code=502,
            content={"error": {"message": str(e), "type": "server_error"}},
        )

    _log_response("/v1/chat/completions", 200, f"finish={full.get('finish_reason')}")
    message = {"role": full["role"], "content": full.get("content", "")}
    if "tool_calls" in full:
        message["tool_calls"] = full["tool_calls"]
    usage = full.get("usage", {
        "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
        "completion_tokens": len(full.get("content", "").split()),
        "total_tokens": 0,
    })
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:16]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": full.get("finish_reason", "stop"),
        }],
        "usage": usage,
    }


@app.get("/v1/models")
async def openai_list_models():
    models = []
    for name in PROVIDER_REGISTRY:
        models.append({
            "id": name,
            "object": "model",
            "created": 1700000000,
            "owned_by": name.split("/")[0],
        })
    return {"object": "list", "data": models}


async def _stream_openai_chat(provider, model: str, messages: list, options: dict) -> AsyncIterator[str]:
    """Stream in OpenAI SSE format with content + tool_calls passthrough."""
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"
    created = int(time.time())
    raw_stream = getattr(provider, "chat_stream_raw", None)

    try:
        if raw_stream:
            async for raw in raw_stream(messages, options=options):
                delta: dict[str, Any] = {}
                if "role" in raw:
                    delta["role"] = raw["role"]
                if "content" in raw:
                    delta["content"] = raw["content"]
                if "tool_calls" in raw:
                    delta["tool_calls"] = raw["tool_calls"]
                finish_reason = raw.get("finish_reason")
                if not delta and not finish_reason:
                    continue
                data = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
                }
                yield f"data: {json.dumps(data)}\n\n"
        else:
            async for chunk in provider.chat_stream(messages, options=options):
                data = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {"index": 0, "delta": {"content": chunk}, "finish_reason": None}
                    ],
                }
                yield f"data: {json.dumps(data)}\n\n"
    except Exception as e:
        logger.exception("Streaming error")
        yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'server_error'}})}\n\n"
        yield "data: [DONE]\n\n"
        return

    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_ns() -> int:
    return time.time_ns()
