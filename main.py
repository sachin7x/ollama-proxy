"""
Fake Ollama API Server
======================
Speaks the Ollama REST protocol on port 11434, routes to cloud LLM providers.

Model naming (set as the "model" field in your client):
  openai/gpt-4o                      xai/grok-2
  openai/gpt-4o-mini                 groq/llama-3.3-70b-versatile
  gemini/gemini-2.5-pro              mistral/mistral-large-latest
  anthropic/claude-sonnet-4-5        deepseek/deepseek-chat
  kimi/kimi-k2.6                     together/meta-llama/Llama-3...
  azure/<deployment-name>            perplexity/sonar-pro
  bedrock/us.anthropic.claude-...

Run:
  uvicorn main:app --host 0.0.0.0 --port 11434 --reload

Optional env:
  PROXY_DEBUG=1                  enable verbose request/response logging
  EXTRA_MODELS=p1/m1,p2/m2       add models to /api/tags without editing config.py
"""

import time
import json
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse

from providers.anthropic_provider import AnthropicProvider
from providers.azure_provider import AzureProvider
from providers.bedrock_provider import BedrockProvider
from providers.openai_compat_provider import OpenAICompatProvider
from config import (
    PROVIDER_REGISTRY,
    API_KEYS,
    AZURE_CONFIG,
    AZURE_DEPLOYMENTS,
    BEDROCK_CONFIG,
    OPENAI_COMPAT_PROVIDERS,
    DEBUG_LOGGING,
)

app = FastAPI(title="Fake Ollama Server", version="1.0.0")

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("ollama-proxy")
if DEBUG_LOGGING:
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.setLevel(logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.setLevel(logging.INFO)


def _log_request(endpoint: str, body: dict):
    """Log request details when debug logging is enabled."""
    if not DEBUG_LOGGING:
        return
    model = body.get("model", "?")
    stream = body.get("stream", "?")
    msgs = body.get("messages", [])
    msg_count = len(msgs) if isinstance(msgs, list) else 0
    tools = body.get("tools", [])
    fmt = body.get("format", None)
    logger.debug(
        f"REQ {endpoint} | model={model} stream={stream} messages={msg_count} "
        f"tools={len(tools) if tools else 0} format={fmt}"
    )
    if msgs and msg_count > 0:
        last = msgs[-1]
        content_preview = str(last.get("content", ""))[:100]
        logger.debug(f"  last_msg: role={last.get('role')} content={content_preview}...")


def _log_response(endpoint: str, status: int, detail: str = ""):
    """Log response details when debug logging is enabled."""
    if not DEBUG_LOGGING:
        return
    logger.debug(f"RES {endpoint} | status={status} {detail}")


# ---------------------------------------------------------------------------
# Provider routing
# ---------------------------------------------------------------------------

def get_provider(model: str):
    """Parse 'provider/model-name' and return the right provider instance."""
    if "/" in model:
        prefix, model_id = model.split("/", 1)
    else:
        prefix, model_id = "openai", model

    prefix = prefix.lower()

    # Providers with non-OpenAI-compatible SDKs
    if prefix in ("anthropic", "claude"):
        return AnthropicProvider(api_key=API_KEYS["anthropic"], model=model_id)
    elif prefix == "azure":
        cfg = AZURE_DEPLOYMENTS.get(model_id, AZURE_CONFIG)
        return AzureProvider(
            api_key=cfg["api_key"],
            model=model_id,
            endpoint=cfg["endpoint"],
            api_version=cfg["api_version"],
        )
    elif prefix == "bedrock":
        return BedrockProvider(
            model=model_id,
            region=BEDROCK_CONFIG["region"],
            profile=BEDROCK_CONFIG["profile"],
        )

    # OpenAI-compatible providers (OpenAI, Kimi, xAI, Groq, Mistral, etc.)
    elif prefix in OPENAI_COMPAT_PROVIDERS:
        cfg = OPENAI_COMPAT_PROVIDERS[prefix]
        return OpenAICompatProvider(
            api_key=cfg["api_key"],
            model=model_id,
            base_url=cfg["base_url"],
        )

    else:
        supported = ", ".join(
            ["anthropic", "azure", "bedrock"]
            + list(OPENAI_COMPAT_PROVIDERS.keys())
        )
        raise ValueError(
            f"Unknown provider prefix: '{prefix}'. Supported: {supported}"
        )


# ---------------------------------------------------------------------------
# Health / version
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Real Ollama returns plain text - some clients check for this exact string."""
    return PlainTextResponse("Ollama is running")


@app.get("/api/version")
async def version():
    return {"version": "0.6.5"}


# ---------------------------------------------------------------------------
# Model listing
# ---------------------------------------------------------------------------

@app.get("/api/tags")
async def list_models():
    """List all available models from PROVIDER_REGISTRY."""
    models = []
    for name in PROVIDER_REGISTRY:
        models.append({
            "name": name,
            "model": name,
            "modified_at": "2025-01-01T00:00:00Z",
            "size": 0,
            "digest": f"sha256:{abs(hash(name)):064x}"[:71],
            "details": {
                "parent_model": "",
                "format": "cloud",
                "family": name.split("/")[0],
                "families": [name.split("/")[0]],
                "parameter_size": "cloud",
                "quantization_level": "none",
            },
        })
    return {"models": models}


@app.get("/api/ps")
async def list_running():
    """
    List currently loaded/running models.
    Cloud proxy has no VRAM concept; empty list keeps Open WebUI happy.
    """
    return {"models": []}


@app.post("/api/show")
async def show_model(request: Request):
    """
    Show model information. Clients verify a model exists here before chatting.
    Allows any 'prefix/model' as long as the prefix is configured —
    so users don't have to register every model in PROVIDER_REGISTRY.
    """
    body = await request.json()
    model = body.get("model", "")

    # Check if the prefix is configured (registry membership is optional)
    if "/" in model:
        prefix = model.split("/", 1)[0].lower()
    else:
        prefix = "openai"

    known_prefixes = (
        {"anthropic", "claude", "azure", "bedrock"}
        | set(OPENAI_COMPAT_PROVIDERS.keys())
    )
    if prefix not in known_prefixes and model not in PROVIDER_REGISTRY:
        return JSONResponse(
            status_code=404,
            content={"error": f"model '{model}' not found"}
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
# Model management (mocked - not applicable for a cloud proxy)
# ---------------------------------------------------------------------------

@app.post("/api/pull")
async def pull_model(request: Request):
    """
    Mock pull with streaming progress events so clients that iterate
    the NDJSON stream don't hang waiting for a response.
    """
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
        content={"error": "push is not supported by this cloud proxy"}
    )


@app.post("/api/create")
async def create_model(request: Request):
    return JSONResponse(
        status_code=501,
        content={"error": "create is not supported by this cloud proxy"}
    )


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

@app.post("/api/embeddings")
async def embeddings_legacy(request: Request):
    """
    Legacy embeddings (pre-v0.1.33).
    Input:  {"model": "...", "prompt": "..."}
    Output: {"embedding": [...]}
    """
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
            content={"error": f"Provider '{model.split('/')[0]}' does not support embeddings."}
        )

    return {"embedding": embedding}


@app.post("/api/embed")
async def embeddings_new(request: Request):
    """
    New embeddings endpoint (v0.1.33+). Used by most modern Ollama clients.
    Input:  {"model": "...", "input": "string" | ["string", ...]}
    Output: {"model": "...", "embeddings": [[...], ...]}
    """
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
            content={"error": f"Provider '{model.split('/')[0]}' does not support embeddings."}
        )

    return {
        "model": model,
        "embeddings": embeddings,
        "total_duration": 0,
        "load_duration": 0,
        "prompt_eval_count": sum(len(t.split()) for t in inputs),
    }


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

@app.post("/api/generate")
async def generate(request: Request):
    """Ollama /api/generate - raw text completion."""
    body = await request.json()
    model = body.get("model", "openai/gpt-4o-mini")
    prompt = body.get("prompt", "")
    system = body.get("system", "")
    stream = body.get("stream", True)
    options = body.get("options", {})
    fmt = body.get("format", None)

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
            media_type="application/x-ndjson"
        )

    try:
        t0 = _now_ns()
        content = await provider.chat(messages, stream=False, options=options)
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
    """Ollama /api/chat - multi-turn chat completion."""
    body = await request.json()
    model = body.get("model", "openai/gpt-4o-mini")
    messages = body.get("messages", [])
    stream = body.get("stream", True)
    options = body.get("options", {})
    tools = body.get("tools", None)
    fmt = body.get("format", None)

    _log_request("/api/chat", body)

    try:
        provider = get_provider(model)
    except ValueError as e:
        _log_response("/api/chat", 400, str(e))
        return JSONResponse(status_code=400, content={"error": str(e)})

    # Pass tools and format via options for providers that support them
    if tools:
        options["_tools"] = tools
    if fmt:
        options["_format"] = fmt

    if stream:
        return StreamingResponse(
            _stream_chat(provider, model, messages, options),
            media_type="application/x-ndjson"
        )

    try:
        t0 = _now_ns()
        content = await provider.chat(messages, stream=False, options=options)
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
# Streaming helpers
# ---------------------------------------------------------------------------

async def _stream_chat(
    provider, model: str, messages: list, options: dict
) -> AsyncIterator[str]:
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


async def _stream_generate(
    provider, model: str, messages: list, options: dict
) -> AsyncIterator[str]:
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
# OpenAI-compatible endpoints (used by Copilot, Continue, etc.)
# ---------------------------------------------------------------------------

@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI-compatible /v1/chat/completions — for clients that use OpenAI format."""
    body = await request.json()
    model = body.get("model", "openai/gpt-4o-mini")
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    tools = body.get("tools", None)

    _log_request("/v1/chat/completions", body)

    # Map OpenAI params to our options format
    # Note: we intentionally skip temperature/top_p unless they are non-default,
    # because some models (e.g. kimi-k2.5) reject custom temperature values.
    options = {}
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
        return JSONResponse(status_code=400, content={"error": {"message": str(e), "type": "invalid_request_error"}})

    # Disable thinking/reasoning for Kimi k2 models when called via OpenAI compat
    # endpoint (Copilot etc. can't handle reasoning tokens in the response)
    extra_body = {}
    prefix = model.split("/")[0].lower() if "/" in model else ""
    if prefix == "kimi":
        extra_body["thinking"] = {"type": "disabled"}

    if extra_body:
        options["_extra_body"] = extra_body

    if stream:
        return StreamingResponse(
            _stream_openai_chat(provider, model, messages, options),
            media_type="text/event-stream"
        )

    try:
        chat_full = getattr(provider, "chat_full", None)
        if chat_full:
            full = await chat_full(messages, options=options)
        else:
            content = await provider.chat(messages, stream=False, options=options)
            full = {"role": "assistant", "content": content, "finish_reason": "stop"}
    except Exception as e:
        _log_response("/v1/chat/completions", 502, str(e))
        return JSONResponse(status_code=502, content={"error": {"message": str(e), "type": "server_error"}})

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
        "id": f"chatcmpl-{abs(hash(str(full))):016x}",
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
    """OpenAI-compatible model listing."""
    models = []
    for name in PROVIDER_REGISTRY:
        models.append({
            "id": name,
            "object": "model",
            "created": 1700000000,
            "owned_by": name.split("/")[0],
        })
    return {"object": "list", "data": models}


async def _stream_openai_chat(
    provider, model: str, messages: list, options: dict
) -> AsyncIterator[str]:
    """Stream in OpenAI SSE format with proper content + tool_calls passthrough."""
    chat_id = f"chatcmpl-{abs(hash(model)):016x}"
    created = int(time.time())
    final_finish_reason = "stop"

    # Use raw streaming if provider supports it (OpenAICompatProvider does)
    raw_stream = getattr(provider, "chat_stream_raw", None)

    try:
        if raw_stream:
            async for raw in raw_stream(messages, options=options):
                delta = {}
                if "role" in raw:
                    delta["role"] = raw["role"]
                if "content" in raw:
                    delta["content"] = raw["content"]
                if "tool_calls" in raw:
                    delta["tool_calls"] = raw["tool_calls"]
                finish_reason = raw.get("finish_reason")
                if finish_reason:
                    final_finish_reason = finish_reason
                if not delta and not finish_reason:
                    continue
                data = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": delta,
                        "finish_reason": finish_reason,
                    }],
                }
                yield f"data: {json.dumps(data)}\n\n"
        else:
            # Fallback for providers without raw streaming (Anthropic, Bedrock, Azure)
            async for chunk in provider.chat_stream(messages, options=options):
                data = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None,
                    }],
                }
                yield f"data: {json.dumps(data)}\n\n"
    except Exception as e:
        logger.exception("Streaming error")
        error_data = {"error": {"message": str(e), "type": "server_error"}}
        yield f"data: {json.dumps(error_data)}\n\n"
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
