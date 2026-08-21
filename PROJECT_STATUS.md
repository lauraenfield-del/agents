# Project Status

This file is a current snapshot of what is actually present in the repository.

## Implemented runtime

- Core event bus, runtime, orchestration, validation, logging, memory, and tool infrastructure are present under `core/`
- `ConversationalAgent` is implemented under `core/runtime/conversational.py`
- Live provider adapters exist for OpenAI and Anthropic under `core/model/`
- `build_agent()` validates a manifest, registers known tools, creates memory, and selects a model

## Implemented tools

The runtime currently includes implementations for:

- filesystem
- terminal
- `web_fetch` (also available as `browser`)
- `web_search`
- `communication` (implemented, but not registered by `build_agent()` by default)
- `think` (sequential thinking)

## Registered packages

The repository currently includes nine registered packages:

- autonomous
- coding
- customer_support
- ad_clicker
- enfieldai
- marketing
- personal_assistant
- research
- social_media

## CLI and demo entry points

- `run_agent.py` launches a package by name
- passing a message runs one turn and exits
- omitting the message starts an interactive REPL
- `demo.py` demonstrates runtime event subscriptions with a simple demo agent

## Model configuration

To use a live model:

- install `openai` and set `OPENAI_API_KEY`, optionally `OPENAI_MODEL`
- or install `anthropic` and set `ANTHROPIC_API_KEY`, optionally `ANTHROPIC_MODEL`

If neither key is configured, the runtime falls back to `MockModel` with a warning.

## Test verification

Verified on 2026-08-09 with:

```bash
python3 -m pytest -q
```

Result:

- 62 passed
- 1 expected warning about falling back to `MockModel` when no API key is configured

## Repository note

The repository also contains a versioned `skills/` directory. That content is currently separate from the Python runtime and is not loaded by `build_agent()` or `run_agent.py`.
