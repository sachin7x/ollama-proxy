"""Command-line entry point for ollama-proxy."""

import argparse
import os
import sys

from . import __version__


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ollama-proxy",
        description="Speak the Ollama API protocol, route to cloud LLM providers.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ollama-proxy {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    # serve (default)
    serve = subparsers.add_parser("serve", help="Run the proxy server (default)")
    _add_serve_args(serve)

    # doctor
    subparsers.add_parser("doctor", help="Check configuration and provider connectivity")

    # list-models
    subparsers.add_parser("list-models", help="Show all configured models")

    # test
    test_p = subparsers.add_parser("test", help="Send a test request to a model")
    test_p.add_argument("model", help="Model name (prefix/model-id)")
    test_p.add_argument("--prompt", default="Say hello in one short sentence.")

    # If no subcommand, treat top-level args as 'serve' args
    _add_serve_args(parser)

    args = parser.parse_args()
    cmd = args.command or "serve"

    if cmd == "serve":
        return _cmd_serve(args)
    if cmd == "doctor":
        from .commands import doctor

        return doctor.run()
    if cmd == "list-models":
        from .commands import list_models

        return list_models.run()
    if cmd == "test":
        from .commands import test

        return test.run(args.model, args.prompt)
    parser.print_help()
    return 1


def _add_serve_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--host", default=os.getenv("PROXY_HOST", "0.0.0.0"), help="Bind host (default: 0.0.0.0)")
    p.add_argument("--port", type=int, default=int(os.getenv("PROXY_PORT", "11434")), help="Port (default: 11434)")
    p.add_argument("--debug", action="store_true", help="Enable verbose request/response logging")
    p.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev only)")
    p.add_argument("--config", help="Path to YAML config file (overrides env vars)")
    p.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (use >1 for production; --reload requires 1)",
    )


def _cmd_serve(args: argparse.Namespace) -> int:
    if args.config:
        os.environ["PROXY_CONFIG_FILE"] = args.config
    if args.debug:
        os.environ["PROXY_DEBUG"] = "1"

    import uvicorn

    uvicorn.run(
        "ollama_proxy.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
