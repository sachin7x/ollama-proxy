# Self-hosted servers

Any server that exposes an OpenAI-compatible REST API works through the
generic adapter. Just add a config entry — no code changes, no new
dependencies.

## Common servers and their default URLs

| Server | Typical Base URL |
|--------|-----------------|
| **vLLM** | `http://localhost:8000/v1` |
| **Ray Serve** (vLLM backend) | `http://localhost:8000/v1` |
| **Hugging Face TGI** | `http://localhost:8080/v1` |
| **LM Studio** | `http://localhost:1234/v1` |
| **LocalAI** | `http://localhost:8080/v1` |
| **Ollama** (a real instance) | `http://localhost:11434/v1` |
| **Llamafile** | `http://localhost:8080/v1` |
| **Jan** | `http://localhost:1337/v1` |

## Quick example: vLLM

Start vLLM:

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --host 0.0.0.0 \
  --port 8000
```

Configure the proxy:

=== "Environment variables"

    ```bash
    export PROVIDERS_VLLM_API_KEY=EMPTY
    export PROVIDERS_VLLM_BASE_URL=http://localhost:8000/v1
    ollama-proxy
    ```

=== "YAML config"

    ```yaml
    # ollama-proxy.yaml
    providers:
      myvllm:
        api_key: EMPTY
        base_url: http://localhost:8000/v1
    ```

    ```bash
    ollama-proxy --config ollama-proxy.yaml
    ```

Call through the proxy:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "vllm/meta-llama/Llama-3.1-8B-Instruct",
  "messages": [{"role": "user", "content": "Hello!"}]
}'
```

## Multiple instances

Use distinct prefixes for different self-hosted servers:

```yaml
providers:
  vllm-7b:
    api_key: EMPTY
    base_url: http://gpu-1:8000/v1
  vllm-70b:
    api_key: EMPTY
    base_url: http://gpu-2:8000/v1
  raycluster:
    api_key: ${RAY_API_KEY}
    base_url: http://ray-head:8000/v1
```

Then:

```
vllm-7b/<model-id>
vllm-70b/<model-id>
raycluster/<model-id>
```

## Notes

- Most self-hosted servers accept any non-empty API key value (`EMPTY` is
  conventional). Some require a specific value — check the server docs.
- If the server is on a remote host, replace `localhost` with the host name
  or IP. Ensure firewalls allow proxy → server traffic.
- Streaming, tool calls, and structured outputs work as long as the server
  supports them. vLLM 0.6+, TGI, and Ollama all do.
