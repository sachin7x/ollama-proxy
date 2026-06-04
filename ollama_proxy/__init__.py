"""ollama-proxy — Speak the Ollama API protocol, route to any cloud LLM."""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("ollama-proxy-plus")
    except PackageNotFoundError:
        # Package not installed (e.g. running from source without install)
        __version__ = "0.0.0+unknown"
except ImportError:
    __version__ = "0.0.0+unknown"

from .server import app

__all__ = ["app", "__version__"]
