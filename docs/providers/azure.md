# Azure OpenAI

Uses the openai SDK's `AzureOpenAI` client. No extra install needed (`openai`
is a core dependency).

## Configure

Azure needs three values:

```bash
export AZURE_OPENAI_API_KEY=<from Azure portal -> Keys & Endpoint>
export AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
export AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

## Use

Prefix: `azure/`. The model ID after the prefix is your **deployment name**
(the name you gave when deploying the model in Azure AI Studio), not the
underlying base model name.

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "azure/my-gpt4o-deployment",
  "messages": [{"role": "user", "content": "Hello!"}]
}'
```

## Multiple resources / API versions

For deployments spread across multiple Azure resources or API versions, use
the `AZURE_DEPLOYMENTS` dict in `config.py`:

```python
AZURE_DEPLOYMENTS = {
    "gpt4o-prod": {
        "api_key": "...",
        "endpoint": "https://prod.openai.azure.com/",
        "api_version": "2024-08-01-preview",
    },
    "gpt35-dev": {
        "api_key": "...",
        "endpoint": "https://dev.openai.azure.com/",
        "api_version": "2024-02-01",
    },
}
```

Deployments not listed here fall back to the default `AZURE_CONFIG`.

## Embeddings

Azure embeddings are supported via `/api/embed` and `/api/embeddings` —
just route through an embedding deployment:

```
azure/my-text-embedding-3-small-deployment
```
