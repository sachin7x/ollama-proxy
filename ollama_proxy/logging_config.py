"""Structured logging with correlation IDs.

Every request gets a unique request_id. JSON output is enabled via
PROXY_LOG_JSON=1 (otherwise a readable text format is used).
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

# Per-request correlation ID — set via middleware, read via filter
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Forward any extra structured fields
        for k, v in record.__dict__.items():
            if k.startswith("ctx_"):
                payload[k[4:]] = v
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(debug: bool, json_format: bool) -> logging.Logger:
    root = logging.getLogger()
    # Clear any existing handlers (uvicorn or basicConfig may have set some)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())

    if json_format:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # Quiet down noisy libraries unless debug
    if not debug:
        for noisy in ("httpcore", "httpx", "urllib3", "boto3", "botocore"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("ollama-proxy")


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]
