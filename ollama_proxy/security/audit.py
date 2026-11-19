"""Append-only, hash-chained audit events (tamper-evident, not immutable)."""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from typing import Any


class AuditLedger:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not event_type:
            raise ValueError("event_type is required")
        with self._lock:
            previous = self._events[-1]["hash"] if self._events else "0" * 64
            event = {"id": str(uuid.uuid4()), "timestamp": time.time(),
                     "event_type": event_type, "payload": payload,
                     "previous_hash": previous}
            encoded = json.dumps(event, sort_keys=True, separators=(",", ":"),
                                 default=str).encode()
            event["hash"] = hashlib.sha256(encoded).hexdigest()
            self._events.append(event)
            return dict(event)

    def verify(self) -> bool:
        with self._lock:
            previous = "0" * 64
            for stored in self._events:
                event = {k: v for k, v in stored.items() if k != "hash"}
                encoded = json.dumps(event, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()
                expected = hashlib.sha256(encoded).hexdigest()
                if stored["previous_hash"] != previous or stored["hash"] != expected:
                    return False
                previous = stored["hash"]
            return True

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(dict(event) for event in self._events)
