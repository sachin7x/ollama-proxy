# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-04

First public PyPI release.

### Added
- CLI entry point: `ollama-proxy` command with `serve` (default), `doctor`,
  `list-models`, and `test` subcommands.
- YAML config file support via `--config` flag or `PROXY_CONFIG_FILE` env var.
- Auto-discovery of OpenAI-compatible providers from
  `PROVIDERS_<NAME>_API_KEY` / `PROVIDERS_<NAME>_BASE_URL` env vars.
- Per-provider retry and fallback configuration in YAML config.
- Health endpoints: `/health` (basic) and `/health/providers` (connectivity).
- Structured logging with per-request correlation IDs (`x-request-id` header).
- JSON log format option via `PROXY_LOG_JSON=1`.
- `EXTRA_MODELS` env var to add models to `/api/tags` without editing config.
- AWS Bedrock provider via boto3 Converse API.
- OpenAI-compatible endpoint at `/v1/chat/completions` with proper tool calls
  and streaming SSE support (for GitHub Copilot, Continue, Cursor).
- `tools` and `format` (JSON mode / JSON schema) pass-through on `/api/chat`.
- Optional dependency groups: `[anthropic]`, `[bedrock]`, `[all]`.

### Changed
- Gemini now routes through Google's OpenAI-compatible endpoint instead of
  the deprecated `google-generativeai` SDK.
- Kimi now uses `api.moonshot.ai` (was `.cn`) and supports thinking-mode
  control via `extra_body`.
- `/api/show` accepts any `prefix/model-id` whose prefix is configured
  (registry membership is no longer required for direct API calls).
- Reported Ollama version bumped to `0.6.5` (some clients require ≥0.6.4).

### Removed
- `google-generativeai` dependency (Gemini handled via OpenAI-compat path).
- Standalone `OpenAIProvider` and `KimiProvider` classes (folded into
  `OpenAICompatProvider` for consistency).
