"""Aura-inspired security primitives for agent tool execution.

This package is an opt-in execution boundary. It does not claim to secure model
inference or arbitrary tools unless callers route every protected operation
through SecurityKernel.execute.
"""
from .kernel import SecurityKernel
from .models import (
    AgentIdentity, AgentManifest, CapabilityGrant, DataLabel, DataValue,
    ExecutionContext, ExecutionDecision, PolicyDecision, RiskLevel,
)
from .policy import PolicyEngine, SecurityPolicy
from .provenance import TaintTracker
from .audit import AuditLedger

__all__ = [
    "SecurityKernel", "AgentIdentity", "AgentManifest", "CapabilityGrant",
    "DataLabel", "DataValue", "ExecutionContext", "ExecutionDecision",
    "PolicyDecision", "RiskLevel", "PolicyEngine", "SecurityPolicy",
    "TaintTracker", "AuditLedger",
]
