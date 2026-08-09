# Agents

This repository currently contains two things:

1. a small Python agent framework built around a shared runtime and manifest-driven packages
2. a `skills/` directory of prompt/content assets that is stored in the repo but is not imported by the Python runtime

The executable framework lives in `core/`, `builders/`, `packages/`, `registry/`, `tests/`, `run_agent.py`, and `demo.py`.

## Repository layout

```text
agents/
├── builders/      Package validation, generation, registration, and runtime assembly
├── core/          Runtime, tools, models, memory, orchestration, and validation code
├── packages/      Six manifest-only agent packages
├── registry/      JSON package indexes
├── skills/        Standalone skill/reference content; not loaded by build_agent()
├── tests/         Pytest suite
├── demo.py        Event bus demonstration
├── run_agent.py   CLI entry point
├── README.md
├── PROJECT_STATUS.md
├── objective.md
├── requirements.txt
└── pytest.ini
```

## What is implemented

### Core runtime

`core/` currently includes:

- `events/` for pub/sub lifecycle events
- `interfaces/` for abstract agent, tool, memory, model, and workflow contracts
- `logging/` for structured logging helpers
- `memory/` for in-memory and file-backed storage
- `model/` for mock, OpenAI, and Anthropic adapters plus provider selection
- `orchestration/` for workflow coordination
- `runtime/` for `AgentRuntime` and `ConversationalAgent`
- `tools/` for filesystem, terminal, `web_fetch`/`web_search` (plus `browser` alias), and sequential thinking (`think`) tools; `communication` is implemented but is not registered by `builders/build_agent.py` by default.
- `validation/` for schema and manifest validation

`AgentRuntime.start()` publishes:

1. `runtime.start`
2. `agent.run.before`
3. `agent.run.after` on success, or `agent.error` on failure
4. `runtime.stop`

### Packaged agents

The repo currently ships these six packages:

| Package | Description |
|---|---|
| `autonomous` | Long-running task execution agent |
| `coding` | Software engineering agent |
| `research` | Research and analysis agent |
| `marketing` | Marketing workflow agent |
| `social_media` | Social media workflow agent |
| `customer_support` | Customer support agent |

Each package is defined by `packages/<name>/agent.yaml`. The manifests declare metadata, tools, workflows, knowledge labels, and an entrypoint workflow name.

### Builders and registry

| Path | Purpose |
|---|---|
| `builders/validate_package.py` | Load and validate an `agent.yaml` manifest |
| `builders/generate_package.py` | Write a new manifest from a Python dictionary |
| `builders/register_package.py` | Validate a package and add it to `registry/package_index.json` |
| `builders/build_agent.py` | Build an `AgentRuntime` from a package directory |
| `registry/package_index.json` | Registered package metadata |
| `registry/agents.json` | Reserved metadata file; currently present but not actively used by the runtime |

## Setup

These instructions were verified with Python 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

`requirements.txt` installs the base development dependencies used by the repository, including `pytest`, `jsonschema`, `PyYAML`, and `requests`.

### Optional live-model dependencies

The base install does **not** install provider SDKs. To use a live hosted model instead of the mock fallback, install one of:

```bash
python3 -m pip install openai
# or
python3 -m pip install anthropic
```

Then configure one of these environment variables:

| Variable | Provider | Default model | Optional override |
|---|---|---|---|
| `OPENAI_API_KEY` | OpenAI | `gpt-4o-mini` | `OPENAI_MODEL` |
| `ANTHROPIC_API_KEY` | Anthropic | `claude-3-haiku-20240307` | `ANTHROPIC_MODEL` |

`builders.build_agent.build_agent()` uses `core.model.factory.create_model()`, which checks `OPENAI_API_KEY` first, then `ANTHROPIC_API_KEY`. If neither key is set, it warns and falls back to `MockModel`.

## Running agents

Run commands from the repository root.

### CLI

`run_agent.py` supports both one-shot and interactive use:

```bash
python3 run_agent.py research "Summarize zero-trust architecture."
python3 run_agent.py coding
```

- with a message: the agent handles one request and exits
- without a message: an interactive REPL starts

Typical startup output begins with:

```text
Building agent from package: research
Agent ready: Research Agent
```

### Demo

`demo.py` is an event-lifecycle demo. It builds the `autonomous` package runtime, swaps in a simple `DemoAgent`, subscribes to runtime events, and then starts the runtime:

```bash
python3 demo.py
```

### Python API

```python
from pathlib import Path
from builders.build_agent import build_agent

runtime = build_agent(Path("packages") / "research")
reply = runtime.start(user_input="Summarize zero-trust architecture.")
print(reply)
```

## Creating and registering a package

```python
from pathlib import Path
from builders.generate_package import generate_package
from builders.register_package import register_package

package_dir = Path("packages") / "my_agent"
manifest = {
    "name": "My Agent",
    "version": "1.0.0",
    "inherits": "core",
    "description": "A short description.",
    "tools": ["filesystem"],
    "workflows": ["main_workflow"],
    "knowledge": ["domain_knowledge"],
    "entrypoint": {"workflow": "main_workflow"},
}

generate_package(package_dir, manifest)
register_package(package_dir)
```

You can then launch it with:

```bash
python3 run_agent.py my_agent
```

## Tests

Run the full suite with:

```bash
python3 -m pytest -q
```

Run a single file with:

```bash
python3 -m pytest tests/test_runtime.py -q
```

Current verified baseline:

- 10 test modules
- 62 passing tests
- `python3 -m pytest -q`

## Notes on `skills/`

The `skills/` tree is currently versioned in this repository, but it is separate from the Python runtime described above:

- `build_agent()` does not load from `skills/`
- `run_agent.py` does not reference `skills/`
- the runtime operates entirely from `core/`, `builders/`, `packages/`, and `registry/`

If you are working on the Python framework, treat `skills/` as adjacent content rather than runtime code.
