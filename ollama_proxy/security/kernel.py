"""Security kernel: all protected tool execution must pass through here."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from .audit import AuditLedger
from .identity import IdentityRegistry, IdentityError
from .models import (
    AgentIdentity, CapabilityGrant, ExecutionContext, ExecutionDecision,
    PolicyDecision,
)
from .policy import PolicyEngine
from .provenance import TaintTracker


class SecurityKernel:
    def __init__(self, signing_secret: bytes | None = None,
                 policy: PolicyEngine | None = None,
                 audit: AuditLedger | None = None) -> None:
        self.identities = IdentityRegistry(signing_secret)
        self.policy = policy or PolicyEngine()
        self.audit = audit or AuditLedger()
        self.provenance = TaintTracker()

    def register_agent(self, manifest):
        identity = self.identities.register(manifest)
        self.audit.append("agent.registered", {"agent_id": manifest.agent_id,
                                                "manifest_digest": identity.manifest_digest})
        return identity

    def revoke_agent(self, agent_id: str) -> None:
        self.identities.revoke(agent_id)
        self.audit.append("agent.revoked", {"agent_id": agent_id})

    async def execute(self, identity: AgentIdentity, grant: CapabilityGrant,
                      context: ExecutionContext,
                      operation: Callable[[], Any | Awaitable[Any]]) -> ExecutionDecision:
        event = {"agent_id": context.agent_id, "task_id": context.task_id,
                 "capability": context.requested_capability, "action": context.action}
        if not callable(operation):
            recorded = self.audit.append("tool.execution_blocked", {
                **event, "decision": PolicyDecision.DENY.value,
                "reason": "operation must be callable",
            })
            return ExecutionDecision(PolicyDecision.DENY, "operation must be callable", recorded["id"])
        try:
            manifest = self.identities.verify(identity)
            if context.agent_id != identity.agent_id:
                raise IdentityError("execution context agent mismatch")
            self.identities.verify_grant(grant, context.agent_id, context.task_id,
                                         context.requested_capability)
            decision, reason = self.policy.evaluate(
                context, manifest.allowed_domains, grant.capabilities
            )
        except IdentityError as exc:
            decision, reason = PolicyDecision.DENY, str(exc)

        event.update({"decision": decision.value, "reason": reason})
        if decision is not PolicyDecision.ALLOW:
            recorded = self.audit.append("tool.execution_blocked", event)
            return ExecutionDecision(decision, reason, recorded["id"])

        try:
            result = operation()
            if hasattr(result, "__await__"):
                result = await result
        except Exception as exc:
            recorded = self.audit.append("tool.execution_error", {
                **event, "error_type": type(exc).__name__,
            })
            raise RuntimeError(f"protected operation failed; audit_event={recorded['id']}") from exc

        recorded = self.audit.append("tool.execution_allowed", event)
        return ExecutionDecision(PolicyDecision.ALLOW, reason, recorded["id"], result)
