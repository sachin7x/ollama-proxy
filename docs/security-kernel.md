# Agent Security Kernel

This package provides Aura-inspired primitives for applications that execute
LLM-proposed tools. It is opt-in and does not automatically secure model
responses, external MCP servers, shell processes, network clients, or tools
that bypass `SecurityKernel.execute()`.

## Security boundary

Every protected tool invocation must call `SecurityKernel.execute()`. The
kernel verifies the registered agent identity, the task-bound short-lived
capability grant, deterministic policy, destination allowlist, provenance
labels, and explicit approval for high/critical operations before calling the
operation.

The model is never the authorization authority.

## Quick start

Generate a signing secret (keep it outside source control):

```bash
export AGENT_SECURITY_SIGNING_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

```python
from ollama_proxy.security import AgentManifest, ExecutionContext, SecurityKernel

kernel = SecurityKernel()
manifest = AgentManifest(
    agent_id="research-agent",
    developer="your-team",
    version="1.0.0",
    capabilities=frozenset({"read", "search"}),
    allowed_domains=frozenset({"docs.example.com"}),
)
identity = kernel.register_agent(manifest)
grant = kernel.identities.issue_grant(manifest, "task-123", {"search"})

context = ExecutionContext(
    agent_id="research-agent",
    task_id="task-123",
    original_intent="Search approved documentation",
    requested_capability="search",
    action="docs.search",
    destination_domain="docs.example.com",
)
decision = await kernel.execute(
    identity, grant, context,
    lambda: search_docs("security"),
)
if decision.decision.value != "allow":
    raise PermissionError(decision.reason)
```

High and critical capabilities (write, delete, send, payment, system.modify and
network.egress) require explicit approval by default. Approval must be
collected from a trusted UI or API, never inferred from model output.

## Provenance

External content must be wrapped with `kernel.provenance.external(value, source)`.
Derived values must use `kernel.provenance.derive(value, *inputs)` so taint
propagates. User-confirmed content may use `verified()`, but this should only
be called after authenticating the user-controlled source.

Tainted or sensitive data is denied at send/write/payment/network egress sinks
by default. This conservative default can be refined with a reviewed
declassification workflow in a future release.

## Cryptography

The initial registry uses HMAC-SHA256 with a server-side secret and an
in-memory manifest registry. This is a single-trust-domain starter design,
not a distributed PKI or hardware attestation. Multi-process deployments need
a shared durable registry, key rotation, revocation propagation and a managed
KMS/HSM. A production cross-organization registry should use asymmetric
signatures (for example Ed25519) and independently verifiable certificates.

## Audit

The in-memory audit ledger uses a SHA-256 hash chain to detect modification
of retained events. It is tamper-evident, not immutable. Production use needs
durable append-only storage, access controls, retention policy, key-backed
signatures and external anchoring.

## Limitations

- Intent alignment is not yet a semantic LLM judge. The original intent is
  captured for policy/audit context; authorization remains deterministic.
- Domain allowlisting only constrains the declared destination field. The
  adapter must derive that field from the actual URL and ensure all network
  traffic is mediated.
- The caller must route every protected action through this kernel.
- No generic system can safely infer that arbitrary natural-language content
  is trusted. Provenance must be attached at ingestion and propagated.
- The security package is not wired into chat inference endpoints because
  those endpoints do not execute returned tool calls.

## Verification

Run:

```bash
uv run pytest tests/security -q
uv run ruff check ollama_proxy/security tests/security
```
