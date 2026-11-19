"""Deterministic reference-monitor policy decisions."""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .models import (
    DataLabel, ExecutionContext, PolicyDecision, RiskLevel,
)
from .provenance import TaintTracker


@dataclass(frozen=True)
class SecurityPolicy:
    capability_risks: dict[str, RiskLevel] = field(default_factory=lambda: {
        "read": RiskLevel.LOW,
        "search": RiskLevel.LOW,
        "write": RiskLevel.HIGH,
        "delete": RiskLevel.CRITICAL,
        "send": RiskLevel.HIGH,
        "payment": RiskLevel.CRITICAL,
        "network.egress": RiskLevel.HIGH,
        "system.modify": RiskLevel.CRITICAL,
    })
    require_approval_for: frozenset[RiskLevel] = frozenset(
        {RiskLevel.HIGH, RiskLevel.CRITICAL}
    )
    sensitive_sink_capabilities: frozenset[str] = frozenset(
        {"send", "write", "network.egress", "payment"}
    )
    block_tainted_to_sensitive_sinks: bool = True


class PolicyEngine:
    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self.policy = policy or SecurityPolicy()

    def evaluate(self, context: ExecutionContext, allowed_domains: frozenset[str],
                 grant_capabilities: frozenset[str]) -> tuple[PolicyDecision, str]:
        if context.requested_capability not in grant_capabilities:
            return PolicyDecision.DENY, "capability is not granted for this task"
        if context.requested_capability not in self.policy.capability_risks:
            return PolicyDecision.DENY, "unknown capabilities are denied by default"
        if context.requested_capability == "network.egress" and not context.destination_domain:
            return PolicyDecision.DENY, "network egress requires an explicit destination domain"
        if context.destination_domain:
            try:
                host = self.normalize_domain(context.destination_domain)
            except ValueError:
                return PolicyDecision.DENY, "invalid destination domain"
            if host not in allowed_domains:
                return PolicyDecision.DENY, "destination domain is not allowlisted"
        if (self.policy.block_tainted_to_sensitive_sinks
                and context.requested_capability in self.policy.sensitive_sink_capabilities
                and TaintTracker.may_flow_to_sensitive_sink(context.data)):
            return PolicyDecision.DENY, "tainted or sensitive data cannot flow to this sink"
        risk = self.policy.capability_risks[context.requested_capability]
        if risk in self.policy.require_approval_for and not context.approval_granted:
            return PolicyDecision.REQUIRE_APPROVAL, f"{risk.value} action requires explicit approval"
        return PolicyDecision.ALLOW, "policy checks passed"

    @staticmethod
    def normalize_domain(value: str) -> str:
        parsed = urlsplit(value if "://" in value else "//" + value)
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("invalid destination domain")
        return parsed.hostname.lower().rstrip(".")
