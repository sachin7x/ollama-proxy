"""Typed models for the agent security boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class DataLabel(str, Enum):
    VERIFIED = "verified"
    TAINTED = "tainted"
    SENSITIVE = "sensitive"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True)
class AgentManifest:
    agent_id: str
    developer: str
    version: str
    capabilities: frozenset[str]
    allowed_domains: frozenset[str] = frozenset()
    public_key: str | None = None

    def __post_init__(self) -> None:
        if not self.agent_id or not self.developer or not self.version:
            raise ValueError("agent_id, developer and version are required")
        if any(not item or item.strip() != item for item in self.capabilities):
            raise ValueError("capabilities must be non-empty normalized strings")
        if any(not domain or "/" in domain for domain in self.allowed_domains):
            raise ValueError("allowed_domains must contain hostnames only")


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    developer: str
    version: str
    manifest_digest: str
    issued_at: int
    signature: str


@dataclass(frozen=True)
class CapabilityGrant:
    grant_id: str
    agent_id: str
    capabilities: frozenset[str]
    issued_at: int
    expires_at: int
    task_id: str
    nonce: str


@dataclass(frozen=True)
class DataValue:
    value: Any
    labels: frozenset[DataLabel] = frozenset({DataLabel.VERIFIED})
    sources: tuple[str, ...] = ()

    @property
    def is_tainted(self) -> bool:
        return DataLabel.TAINTED in self.labels

    @property
    def is_sensitive(self) -> bool:
        return DataLabel.SENSITIVE in self.labels


@dataclass(frozen=True)
class ExecutionContext:
    agent_id: str
    task_id: str
    original_intent: str
    requested_capability: str
    action: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    data: tuple[DataValue, ...] = ()
    approval_granted: bool = False
    destination_domain: str | None = None


@dataclass(frozen=True)
class ExecutionDecision:
    decision: PolicyDecision
    reason: str
    audit_event_id: str
    result: Any = None
