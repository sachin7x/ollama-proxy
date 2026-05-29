"""
Tests for ollama-proxy endpoints.

Non-LLM endpoints are tested directly via FastAPI TestClient (no API keys needed).
LLM endpoints (chat / generate / embed) use a patched mock provider so they
run in CI without real credentials.

Run:
    uv run test
    # or
    pytest tests/ -v
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# ── app import ────────────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app

client = TestClient(app)


# =============================================================================
# Health & version
# =============================================================================

class TestHealth:
    def test_root_returns_plain_text(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.text == "Ollama is running"
        assert "text/plain" in r.headers["content-type"]

    def test_version(self):
        r = client.get("/api/version")
        assert r.status_code == 200
        assert "version" in r.json()


# =============================================================================
# Model listing
# =============================================================================

class TestModelListing:
    def test_tags_returns_models_list(self):
        r = client.get("/api/tags")
        assert r.status_code == 200
        body = r.json()
        assert "models" in body
        assert len(body["models"]) > 0

    def test_tags_model_has_required_fields(self):
        models = client.get("/api/tags").json()["models"]
        for m in models:
            assert "name" in m
            assert "model" in m
            assert "details" in m
            assert "digest" in m

    def test_tags_all_providers_present(self):
        names = {m["name"].split("/")[0] for m in client.get("/api/tags").json()["models"]}
        expected = {"openai", "gemini", "anthropic", "kimi", "xai", "groq",
                    "mistral", "deepseek", "together", "perplexity"}
        assert expected.issubset(names)

    def test_ps_returns_empty_models(self):
        r = client.get("/api/ps")
        assert r.status_code == 200
        assert r.json() == {"models": []}


# =============================================================================
# /api/show
# =============================================================================

class TestShowModel:
    def test_show_known_model(self):
        r = client.post("/api/show", json={"model": "openai/gpt-4o"})
        assert r.status_code == 200
        body = r.json()
        assert body["model"] == "openai/gpt-4o"
        assert "details" in body
        assert "modelfile" in body
        assert "capabilities" in body

    def test_show_unknown_model_returns_404(self):
        r = client.post("/api/show", json={"model": "unknown/does-not-exist"})
        assert r.status_code == 404
        assert "error" in r.json()

    def test_show_all_registry_models(self):
        from config import PROVIDER_REGISTRY
        for model in PROVIDER_REGISTRY:
            r = client.post("/api/show", json={"model": model})
            assert r.status_code == 200, f"show failed for {model}"


# =============================================================================
# Model management mocks
# =============================================================================

class TestModelManagement:
    def test_pull_streaming_response(self):
        r = client.post("/api/pull", json={"model": "openai/gpt-4o", "stream": True})
        assert r.status_code == 200
        lines = [l for l in r.text.strip().splitlines() if l]
        assert len(lines) >= 1
        last = json.loads(lines[-1])
        assert last["status"] == "success"

    def test_pull_non_streaming(self):
        r = client.post("/api/pull", json={"model": "openai/gpt-4o", "stream": False})
        assert r.status_code == 200
        assert r.json()["status"] == "success"

    def test_delete_returns_200(self):
        r = client.request("DELETE", "/api/delete", json={"model": "openai/gpt-4o"})
        assert r.status_code == 200

    def test_copy_returns_200(self):
        r = client.post("/api/copy", json={"source": "openai/gpt-4o", "destination": "openai/gpt-4o-copy"})
        assert r.status_code == 200

    def test_push_returns_501(self):
        r = client.post("/api/push", json={"model": "openai/gpt-4o"})
        assert r.status_code == 501
        assert "error" in r.json()

    def test_create_returns_501(self):
        r = client.post("/api/create", json={"model": "mymodel", "modelfile": "FROM openai/gpt-4o"})
        assert r.status_code == 501
        assert "error" in r.json()


# =============================================================================
# /api/chat  (mocked provider)
# =============================================================================

MOCK_PROVIDER_PATH = "main.get_provider"


def make_mock_provider(response_text="Hello from mock!"):
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=response_text)

    async def fake_stream(messages, options=None):
        for word in response_text.split():
            yield word + " "

    provider.chat_stream = fake_stream
    return provider


class TestChat:
    def test_chat_non_streaming(self):
        with patch(MOCK_PROVIDER_PATH, return_value=make_mock_provider("Hi there!")):
            r = client.post("/api/chat", json={
                "model": "openai/gpt-4o",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            })
        assert r.status_code == 200
        body = r.json()
        assert body["message"]["role"] == "assistant"
        assert body["message"]["content"] == "Hi there!"
        assert body["done"] is True
        assert body["done_reason"] == "stop"
        assert "eval_count" in body
        assert "total_duration" in body
        assert "prompt_eval_count" in body

    def test_chat_streaming_chunks(self):
        with patch(MOCK_PROVIDER_PATH, return_value=make_mock_provider("one two three")):
            r = client.post("/api/chat", json={
                "model": "openai/gpt-4o",
                "messages": [{"role": "user", "content": "Count"}],
                "stream": True,
            })
        assert r.status_code == 200
        lines = [l for l in r.text.strip().splitlines() if l]
        assert len(lines) >= 2
        # all but last should have done=False
        for line in lines[:-1]:
            chunk = json.loads(line)
            assert chunk["done"] is False
            assert "message" in chunk
        # last line is done sentinel
        final = json.loads(lines[-1])
        assert final["done"] is True
        assert final["done_reason"] == "stop"
        assert "eval_count" in final
        assert "total_duration" in final

    def test_chat_unknown_provider_returns_400(self):
        r = client.post("/api/chat", json={
            "model": "unknownprovider/some-model",
            "messages": [{"role": "user", "content": "Hi"}],
        })
        assert r.status_code == 400
        assert "error" in r.json()


# =============================================================================
# /api/generate  (mocked provider)
# =============================================================================

class TestGenerate:
    def test_generate_non_streaming(self):
        with patch(MOCK_PROVIDER_PATH, return_value=make_mock_provider("Paris.")):
            r = client.post("/api/generate", json={
                "model": "openai/gpt-4o",
                "prompt": "Capital of France?",
                "stream": False,
            })
        assert r.status_code == 200
        body = r.json()
        assert body["response"] == "Paris."
        assert body["done"] is True
        assert body["done_reason"] == "stop"
        assert "eval_count" in body
        assert "context" in body

    def test_generate_streaming(self):
        with patch(MOCK_PROVIDER_PATH, return_value=make_mock_provider("The answer is 42")):
            r = client.post("/api/generate", json={
                "model": "gemini/gemini-2.0-flash",
                "prompt": "What is the answer?",
                "stream": True,
            })
        assert r.status_code == 200
        lines = [l for l in r.text.strip().splitlines() if l]
        final = json.loads(lines[-1])
        assert final["done"] is True
        assert final["done_reason"] == "stop"

    def test_generate_with_system_prompt(self):
        with patch(MOCK_PROVIDER_PATH, return_value=make_mock_provider("Bonjour!")):
            r = client.post("/api/generate", json={
                "model": "openai/gpt-4o",
                "prompt": "Say hi",
                "system": "You speak only French.",
                "stream": False,
            })
        assert r.status_code == 200
        assert r.json()["done"] is True


# =============================================================================
# /api/embeddings and /api/embed  (mocked provider)
# =============================================================================

def make_embed_provider(vec=None):
    if vec is None:
        vec = [0.1, 0.2, 0.3]
    provider = MagicMock()
    provider.embed = AsyncMock(return_value=vec)
    return provider


class TestEmbeddings:
    def test_legacy_embeddings(self):
        with patch(MOCK_PROVIDER_PATH, return_value=make_embed_provider([0.1, 0.2, 0.3])):
            r = client.post("/api/embeddings", json={
                "model": "openai/text-embedding-3-small",
                "prompt": "hello world",
            })
        assert r.status_code == 200
        body = r.json()
        assert "embedding" in body
        assert isinstance(body["embedding"], list)
        assert len(body["embedding"]) == 3

    def test_new_embed_single_string(self):
        with patch(MOCK_PROVIDER_PATH, return_value=make_embed_provider([0.4, 0.5])):
            r = client.post("/api/embed", json={
                "model": "openai/text-embedding-3-small",
                "input": "single string",
            })
        assert r.status_code == 200
        body = r.json()
        assert "embeddings" in body
        assert len(body["embeddings"]) == 1
        assert body["embeddings"][0] == [0.4, 0.5]
        assert "model" in body

    def test_new_embed_array_input(self):
        with patch(MOCK_PROVIDER_PATH, return_value=make_embed_provider([0.1, 0.2])):
            r = client.post("/api/embed", json={
                "model": "openai/text-embedding-3-small",
                "input": ["text one", "text two", "text three"],
            })
        assert r.status_code == 200
        body = r.json()
        assert len(body["embeddings"]) == 3
