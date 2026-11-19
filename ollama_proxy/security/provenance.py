"""Conservative taint propagation and sensitive-data detection."""
from __future__ import annotations

import re
from .models import DataLabel, DataValue


class TaintTracker:
    _patterns = (
        re.compile(r"(?i)\b[A-Z]{5}[0-9]{4}[A-Z]\b"),  # PAN-like identifier
        re.compile(r"\b\d{12}\b"),                    # Aadhaar-like digit sequence; not validity proof
        re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),        # payment-card-like number
    )

    def external(self, value: object, source: str) -> DataValue:
        if not source:
            raise ValueError("source is required")
        labels = {DataLabel.TAINTED}
        if self.contains_sensitive(value):
            labels.add(DataLabel.SENSITIVE)
        return DataValue(value=value, labels=frozenset(labels), sources=(source,))

    def verified(self, value: object, source: str = "user") -> DataValue:
        if not source:
            raise ValueError("source is required")
        labels = {DataLabel.VERIFIED}
        if self.contains_sensitive(value):
            labels.add(DataLabel.SENSITIVE)
        return DataValue(value=value, labels=frozenset(labels), sources=(source,))

    def derive(self, value: object, *inputs: DataValue) -> DataValue:
        labels: set[DataLabel] = set()
        sources: set[str] = set()
        for item in inputs:
            labels.update(item.labels)
            sources.update(item.sources)
        if not labels:
            labels.add(DataLabel.TAINTED)
        if self.contains_sensitive(value):
            labels.add(DataLabel.SENSITIVE)
        return DataValue(value=value, labels=frozenset(labels), sources=tuple(sorted(sources)))

    @classmethod
    def contains_sensitive(cls, value: object) -> bool:
        text = value if isinstance(value, str) else repr(value)
        return any(pattern.search(text) for pattern in cls._patterns)

    @staticmethod
    def may_flow_to_sensitive_sink(values: tuple[DataValue, ...]) -> bool:
        return any(item.is_tainted or item.is_sensitive for item in values)
