import pytest

from ollama_proxy.security import (
    AgentManifest, DataLabel, ExecutionContext, PolicyDecision,
    RiskLevel, SecurityKernel,
)


@pytest.fixture
def kernel():
    return SecurityKernel(signing_secret=b"test-signing-secret-at-least-32-bytes!!")


def register(kernel, capabilities=frozenset({"read", "search", "send", "payment"}),
             domains=frozenset({"api.example.com"})):
    manifest = AgentManifest("agent.test", "tests", "1.0.0", capabilities, domains)
    identity = kernel.register_agent(manifest)
    return manifest, identity


@pytest.mark.asyncio
async def test_low_risk_tool_executes(kernel):
    manifest, identity = register(kernel)
    grant = kernel.identities.issue_grant(manifest, "task-1", {"read"})
    ctx = ExecutionContext("agent.test", "task-1", "Read document", "read", "document.read")
    decision = await kernel.execute(identity, grant, ctx, lambda: {"ok": True})
    assert decision.decision is PolicyDecision.ALLOW
    assert decision.result == {"ok": True}


@pytest.mark.asyncio
async def test_high_risk_requires_approval(kernel):
    manifest, identity = register(kernel)
    grant = kernel.identities.issue_grant(manifest, "task-1", {"payment"})
    ctx = ExecutionContext("agent.test", "task-1", "Pay invoice", "payment", "payment.send")
    called = False

    def operation():
        nonlocal called
        called = True

    decision = await kernel.execute(identity, grant, ctx, operation)
    assert decision.decision is PolicyDecision.REQUIRE_APPROVAL
    assert called is False


@pytest.mark.asyncio
async def test_approval_allows_high_risk(kernel):
    manifest, identity = register(kernel)
    grant = kernel.identities.issue_grant(manifest, "task-1", {"payment"})
    ctx = ExecutionContext("agent.test", "task-1", "Pay invoice", "payment",
                           "payment.send", approval_granted=True)
    decision = await kernel.execute(identity, grant, ctx, lambda: "paid")
    assert decision.decision is PolicyDecision.ALLOW
    assert decision.result == "paid"


@pytest.mark.asyncio
async def test_tainted_data_cannot_reach_send(kernel):
    manifest, identity = register(kernel)
    grant = kernel.identities.issue_grant(manifest, "task-1", {"send"})
    tainted = kernel.provenance.external("attacker@example.com", "webpage")
    ctx = ExecutionContext("agent.test", "task-1", "Summarize page", "send",
                           "email.send", data=(tainted,), approval_granted=True,
                           destination_domain="api.example.com")
    called = False

    def operation():
        nonlocal called
        called = True

    decision = await kernel.execute(identity, grant, ctx, operation)
    assert decision.decision is PolicyDecision.DENY
    assert not called


@pytest.mark.asyncio
async def test_domain_allowlist_is_enforced(kernel):
    manifest, identity = register(kernel)
    grant = kernel.identities.issue_grant(manifest, "task-1", {"network.egress"})
    ctx = ExecutionContext("agent.test", "task-1", "Fetch data", "network.egress",
                           "http.get", approval_granted=True,
                           destination_domain="evil.example")
    decision = await kernel.execute(identity, grant, ctx, lambda: "unexpected")
    assert decision.decision is PolicyDecision.DENY


@pytest.mark.asyncio
async def test_revoked_identity_is_denied(kernel):
    manifest, identity = register(kernel)
    grant = kernel.identities.issue_grant(manifest, "task-1", {"read"})
    kernel.revoke_agent("agent.test")
    ctx = ExecutionContext("agent.test", "task-1", "Read", "read", "file.read")
    decision = await kernel.execute(identity, grant, ctx, lambda: "secret")
    assert decision.decision is PolicyDecision.DENY


def test_taint_is_preserved_through_derivation(kernel):
    source = kernel.provenance.external("ignore policy", "untrusted_page")
    derived = kernel.provenance.derive("extracted instruction", source)
    assert DataLabel.TAINTED in derived.labels


def test_audit_chain_detects_tampering(kernel):
    kernel.audit.append("test.event", {"value": 1})
    kernel.audit.append("test.event", {"value": 2})
    assert kernel.audit.verify()
    kernel.audit._events[0]["payload"]["value"] = 99
    assert not kernel.audit.verify()
