"""
Fake Ollama API Server
======================
Speaks the Ollama REST protocol on port 11434, routes to cloud LLM providers.

Model naming (set as the "model" field in your client):
  openai/gpt-4o                      xai/grok-2
  openai/gpt-4o-mini                 groq/llama-3.3-70b-versatile
  gemini/gemini-1.5-pro              mistral/mistral-large-latest
  anthropic/claude-3-5-sonnet-...    deepseek/deepseek-chat
  kimi/moonshot-v1-8k                together/meta-llama/Llama-3...
  azure/<deployment-name>            perplexity/sonar-pro

Run:
  uvicorn main:app --host 0.0.0.0 --port 11434 --reload
"""

import time
import json
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse

from providers.openai_provider import OpenAIProvider
from providers.gemini_provider import GeminiProvider
from providers.anthropic_provider import AnthropicProvider
from providers.kimi_provider import KimiProvider
from providers.azure_provider import AzureProvider
from providers.openai_compat_provider import OpenAICompatProvider
from config import (
    PROVIDER_REGISTRY,
    API_KEYS,
    AZURE_CONFIG,
    AZURE_DEPLOYMENTS,
    OPENAI_COMPAT_PROVIDERS,
)

app = FastAPI(title="Fake Ollama Server", version="1.0.0")


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

    # Native providers with their own SDKs
    if prefix == "openai":
        return OpenAIProvider(api_key=API_KEYS["openai"], model=model_id)
    elif prefix == "gemini":
        return GeminiProvider(api_key=API_KEYS["gemini"], model=model_id)
    elif prefix in ("anthropic", "claude"):
        return AnthropicProvider(api_key=API_KEYS["anthropic"], model=model_id)
    elif prefix == "kimi":
        return KimiProvider(api_key=API_KEYS["kimi"], model=model_id)
    elif prefix == "azure":
        cfg = AZURE_DEPLOYMENTS.get(model_id, AZURE_CONFIG)
        return AzureProvider(
            api_key=cfg["api_key"],
            model=model_id,
            endpoint=cfg["endpoint"],
            api_version=cfg["api_version"],
        )

    # OpenAI-compatible providers - all handled by one generic adapter
    elif prefix in OPENAI_COMPAT_PROVIDERS:
        cfg = OPENAI_COMPAT_PROVIDERS[prefix]
        return OpenAICompatProvider(
            api_key=cfg["api_key"],
            model=model_id,
            base_url=cfg["base_url"],
        )

    else:
        supported = ", ".join(
            ["openai", "gemini", "anthropic", "kimi", "azure"]
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
    return {"version": "0.1.0"}


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
    Returns a plausible mock so clients proceed without error.
    """
    body = await request.json()
    model = body.get("model", "")

    if model not in PROVIDER_REGISTRY:
        return JSONResponse(
            status_code=404,
            content={"error": f"model '{model}' not found"}
        )

    provider = model.split("/")[0] if "/" in model else "openai"
    return {
        "model": model,
        "modelfile": f"# Modelfile for {model}\nFROM {model}\n",
        "parameters": "temperature 0.8\nstop \"<|end|>\"",
        "template": "{{ .System }}\n{{ .Prompt }}",
        "details": {
            "parent_model": "",
            "format": "cloud",
            "family": provider,
            "families": [provider],
            "parameter_size": "cloud",
            "quantization_level": "none",
        },
        "model_info": {
            "general.architecture": provider,
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

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        provider = get_provider(model)
    except ValueError as e:
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

    try:
        provider = get_provider(model)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

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
        return JSONResponse(status_code=502, content={"error": str(e)})
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
# Utilities
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_ns() -> int:
    return time.time_ns()
