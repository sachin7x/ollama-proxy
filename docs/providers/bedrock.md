# AWS Bedrock

Uses the `boto3` Converse API, which provides a unified interface across all
Bedrock-hosted models (Claude, Nova, Llama, Mistral, …).

## Install

```bash
pip install "ollama-proxy-plus[bedrock]"
```

## Configure

Bedrock uses the standard AWS credential chain — no API key. Use any of:

=== "Explicit credentials"

    ```bash
    export AWS_ACCESS_KEY_ID=AKIA...
    export AWS_SECRET_ACCESS_KEY=...
    export AWS_REGION=us-east-1
    ```

=== "Named profile"

    ```bash
    export AWS_PROFILE=my-bedrock-profile
    ```

=== "IAM role"

    No env vars needed. Run on EC2, ECS, EKS, or Lambda with an attached IAM
    role and `boto3` picks it up automatically.

## Use

Prefix: `bedrock/`. The model ID is the Bedrock model ID or cross-region
inference profile ID:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0",
  "messages": [{"role": "user", "content": "Hello!"}]
}'
```

## Common model IDs

```
bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0
bedrock/us.amazon.nova-pro-v1:0
bedrock/us.amazon.nova-lite-v1:0
bedrock/us.meta.llama3-1-70b-instruct-v1:0
bedrock/us.mistral.mistral-large-2407-v1:0
```

!!! warning "Enable model access first"
    You must explicitly enable model access in the Bedrock console
    (`Bedrock → Model access`) for each model you want to use.

## Implementation notes

- The Converse API gives a uniform request/response format across vendors.
- Streaming via `converse_stream` is supported and yields incremental text.
- `boto3` is synchronous, so the proxy wraps calls with `asyncio.to_thread`
  to avoid blocking the FastAPI event loop.
- IAM permissions required: `bedrock:InvokeModel` and
  `bedrock:InvokeModelWithResponseStream`.
