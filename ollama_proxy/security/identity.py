"""Local HMAC-signed agent identities and short-lived capability grants.

HMAC is suitable for a single-trust-domain starter implementation. For a
multi-party registry, replace this signer with Ed25519 and a managed key store.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from dataclasses import asdict
from typing import Any

from .models import AgentIdentity, AgentManifest, CapabilityGrant


class IdentityError(ValueError):
    pass


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


class IdentityRegistry:
    def __init__(self, secret: bytes | None = None) -> None:
        self._secret = secret or os.getenv("AGENT_SECURITY_SIGNING_KEY", "").encode()
        if len(self._secret) < 32:
            raise ValueError("AGENT_SECURITY_SIGNING_KEY must contain at least 32 bytes")
        self._manifests: dict[str, AgentManifest] = {}
        self._revoked: set[str] = set()

    def register(self, manifest: AgentManifest) -> AgentIdentity:
        payload = asdict(manifest)
        payload["capabilities"] = sorted(manifest.capabilities)
        payload["allowed_domains"] = sorted(manifest.allowed_domains)
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        issued = int(time.time())
        claims = {"agent_id": manifest.agent_id, "developer": manifest.developer,
                  "version": manifest.version, "manifest_digest": digest,
                  "issued_at": issued}
        signature = hmac.new(self._secret, _canonical(claims), hashlib.sha256).hexdigest()
        self._manifests[manifest.agent_id] = manifest
        self._revoked.discard(manifest.agent_id)
        return AgentIdentity(**claims, signature=signature)

    def verify(self, identity: AgentIdentity) -> AgentManifest:
        manifest = self._manifests.get(identity.agent_id)
        if manifest is None or identity.agent_id in self._revoked:
            raise IdentityError("unknown or revoked agent")
        payload = asdict(manifest)
        payload["capabilities"] = sorted(manifest.capabilities)
        payload["allowed_domains"] = sorted(manifest.allowed_domains)
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        claims = {"agent_id": identity.agent_id, "developer": identity.developer,
                  "version": identity.version, "manifest_digest": identity.manifest_digest,
                  "issued_at": identity.issued_at}
        expected = hmac.new(self._secret, _canonical(claims), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(identity.signature, expected):
            raise IdentityError("invalid identity signature")
        if digest != identity.manifest_digest:
            raise IdentityError("registered manifest changed")
        return manifest

    def revoke(self, agent_id: str) -> None:
        if agent_id not in self._manifests:
            raise IdentityError("unknown agent")
        self._revoked.add(agent_id)

    def issue_grant(self, manifest: AgentManifest, task_id: str,
                    capabilities: set[str] | frozenset[str],
                    ttl_seconds: int = 300) -> CapabilityGrant:
        if not task_id or ttl_seconds < 1 or ttl_seconds > 3600:
            raise ValueError("task_id is required and ttl must be between 1 and 3600 seconds")
        requested = frozenset(capabilities)
        if not requested or not requested.issubset(manifest.capabilities):
            raise IdentityError("requested capabilities exceed agent manifest")
        now = int(time.time())
        return CapabilityGrant(
            grant_id=str(uuid.uuid4()), agent_id=manifest.agent_id,
            capabilities=requested, issued_at=now, expires_at=now + ttl_seconds,
            task_id=task_id, nonce=secrets.token_urlsafe(18),
        )

    @staticmethod
    def verify_grant(grant: CapabilityGrant, agent_id: str, task_id: str,
                     capability: str, now: int | None = None) -> None:
        current = int(time.time()) if now is None else now
        if grant.agent_id != agent_id or grant.task_id != task_id:
            raise IdentityError("grant principal or task mismatch")
        if current < grant.issued_at or current >= grant.expires_at:
            raise IdentityError("grant expired or not yet valid")
        if capability not in grant.capabilities:
            raise IdentityError("capability not granted")
