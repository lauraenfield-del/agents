# Agents

A modular, plug-and-play agent framework built around a single **Core Runtime** and a collection of **specialized Agent Packages**.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [Core Runtime](#core-runtime)
  - [Agent Packages](#agent-packages)
  - [Builders](#builders)
  - [Registry](#registry)
- [Directory Structure](#directory-structure)
- [Available Packages](#available-packages)
- [Installation and Setup](#installation-and-setup)
- [Running an Agent](#running-an-agent)
  - [Option A — run\_agent.py (recommended)](#option-a--run_agentpy-recommended)
  - [Option B — demo.py (event-driven demo)](#option-b--demopy-event-driven-demo)
  - [Option C — Python API](#option-c--python-api)
- [Creating a New Package](#creating-a-new-package)
  - [1. Generate the package scaffold](#1-generate-the-package-scaffold)
  - [2. Register the package](#2-register-the-package)
  - [3. Run the new agent](#3-run-the-new-agent)
- [Running Tests](#running-tests)

---

## Overview

This repository is a **central hub for AI agents**.

At its heart is a single, domain-agnostic **Core Runtime** that handles every cross-cutting concern shared by all agents: execution lifecycle, memory, tools, events, logging, safety, and validation.

Surrounding the core are **specialized Agent Packages** — self-contained directories that plug into the Core Runtime and give an agent its personality, workflows, tools, and domain knowledge.

```
Core Runtime  ←  the foundation every agent shares
     │
     ├── autonomous/   Long-running task execution agent
     ├── coding/       Software engineering agent
     ├── research/     Information gathering & analysis agent
     ├── marketing/    Marketing automation agent
     ├── social_media/ Social media management agent
     └── customer_support/  Customer support agent
```

No package ever modifies the Core Runtime.  
All specialization is achieved through **composition**: pick a package, load it into the runtime, run.

---

## Architecture

### Core Runtime

Located in `core/`, the runtime is the authoritative foundation for every agent.

```
core/
├── events/        Event bus — publish/subscribe between runtime components
├── interfaces/    Abstract base classes (Agent, Tool, Memory, Model)
├── logging/       Structured logger factory
├── memory/        In-process memory store (SimpleMemory)
├── model/         Model abstraction + MockModel for local testing
├── orchestration/ Workflow coordination
├── runtime/       AgentRuntime — the main execution engine
├── tools/         Built-in tools (FileSystemTool) + ToolManager
└── validation/    Schema and manifest validation helpers
```

`AgentRuntime` wires everything together:

```
AgentRuntime(agent, event_bus, tool_manager, memory, model)
      │
      └── runtime.start()
              │
              ├── event_bus.publish("runtime.start")
              ├── event_bus.publish("agent.run.before")
              ├── agent.run()                    ← the package's entrypoint
              ├── event_bus.publish("agent.run.after")   (only if agent.run succeeds)
              ├── event_bus.publish("agent.error", e)    (if agent.run raises)
              └── event_bus.publish("runtime.stop")
```

### Agent Packages

Located in `packages/`, each package is a directory that must contain exactly one `agent.yaml` manifest:

```yaml
name: Autonomous Agent
version: 1.0.0
inherits: core
description: Long-running autonomous task execution agent
tools:
  - browser
  - terminal
  - filesystem
workflows:
  - planning
  - execution
  - evaluation
knowledge:
  - autonomy
entrypoint:
  workflow: autonomous_controller
```

The manifest is the complete contract between a package and the runtime.

### Builders

Located in `builders/`, these utilities automate the full package lifecycle:

| Script | Purpose |
|---|---|
| `validate_package.py` | Loads and validates an `agent.yaml` manifest |
| `generate_package.py` | Writes a new `agent.yaml` from a Python dict |
| `register_package.py` | Validates a package and adds it to `registry/package_index.json` |
| `build_agent.py` | Validates, wires tools + memory + model, returns a ready `AgentRuntime` |

### Registry

Located in `registry/`, two JSON files track the installed package universe:

| File | Contents |
|---|---|
| `package_index.json` | Name, version, description, path, and entrypoint for every registered package |
| `agents.json` | Reserved for additional agent metadata |

---

## Directory Structure

```
agents/
│
├── core/                  Core Runtime (shared by every agent)
│   ├── events/
│   ├── interfaces/
│   ├── logging/
│   ├── memory/
│   ├── model/
│   ├── orchestration/
│   ├── runtime/
│   ├── tools/
│   └── validation/
│
├── packages/              Specialized Agent Packages
│   ├── autonomous/
│   ├── coding/
│   ├── customer_support/
│   ├── marketing/
│   ├── research/
│   └── social_media/
│
├── registry/              Package discovery index
│   ├── agents.json
│   └── package_index.json
│
├── builders/              Package lifecycle utilities
│   ├── build_agent.py
│   ├── generate_package.py
│   ├── register_package.py
│   └── validate_package.py
│
├── tests/                 Test suite
├── demo.py                Event-driven demo
├── run_agent.py           CLI entry point
├── requirements.txt       Python dependencies
└── pytest.ini             Test configuration
```

---

## Available Packages

| Package | Description |
|---|---|
| `autonomous` | Long-running autonomous task execution agent |
| `coding` | Software engineering agent |
| `research` | Information gathering and analysis agent |
| `marketing` | Marketing automation agent |
| `social_media` | Social media management agent |
| `customer_support` | Customer support agent |

---

## Installation and Setup

These instructions assume **Python 3.12** or later. Every command must be run from the **root of this repository**.

### 1. Clone the repository

```bash
git clone https://github.com/lauraenfield-del/agents.git
cd agents
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```cmd
.venv\Scripts\activate.bat
```

Your shell prompt will change to show `(.venv)` when the environment is active.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---|---|
| `pytest` | Test runner |
| `jsonschema` | JSON schema validation |
| `PyYAML` | YAML manifest parsing |

### 5. Configure LLM credentials

The framework auto-selects a real LLM provider based on which API key is set.
Set **one** of the following environment variables before running any agent:

| Variable | Provider | Default model | Model override |
|---|---|---|---|
| `OPENAI_API_KEY` | OpenAI | `gpt-4o-mini` | `OPENAI_MODEL` |
| `ANTHROPIC_API_KEY` | Anthropic | `claude-3-haiku-20240307` | `ANTHROPIC_MODEL` |

**macOS / Linux:**

```bash
export OPENAI_API_KEY=sk-...          # use your real key
# or
export ANTHROPIC_API_KEY=sk-ant-...   # use your real key
```

**Windows (PowerShell):**

```powershell
$env:OPENAI_API_KEY = "sk-..."          # use your real key
# or
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # use your real key
```

**Optional — override the default model (macOS / Linux):**

```bash
export OPENAI_MODEL=gpt-4o            # any OpenAI model name
export ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**Optional — override the default model (Windows PowerShell):**

```powershell
$env:OPENAI_MODEL = "gpt-4o"
$env:ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
```

If neither key is set, `build_agent` falls back to `MockModel` and emits a
`RuntimeWarning`. This is intentional so that tests and local exploration work
without credentials.

### 6. Verify the installation

```bash
python -c "from builders.build_agent import build_agent; print('Setup OK')"
```

Expected output:

```
Setup OK
```

---

## Running an Agent

All commands must be run from the **root of the repository** with the virtual environment **active**.

### Option A — run\_agent.py (recommended)

`run_agent.py` is the standard CLI entry point. Pass it the name of any package in the `packages/` directory.

**Run the autonomous agent:**

```bash
python run_agent.py autonomous
```

**Run the research agent:**

```bash
python run_agent.py research
```

**Run any other package** by substituting its directory name:

```bash
python run_agent.py coding
python run_agent.py marketing
python run_agent.py social_media
python run_agent.py customer_support
```

**Expected output (autonomous example):**

```
Building agent from package: autonomous
Starting agent: Autonomous Agent
{"timestamp": "...", "level": "INFO", "name": "AgentRuntime", "message": "Agent runtime starting."}
{"timestamp": "...", "level": "INFO", "name": "AgentRuntime", "message": "Agent runtime stopped."}
Agent finished.
```

The runtime:

1. Loads and validates the package's `agent.yaml`
2. Registers the tools declared in the manifest
3. Wires up memory and a model
4. Calls `runtime.start()`, which fires the full agent lifecycle and logs progress

### Option B — demo.py (event-driven demo)

`demo.py` demonstrates the full event lifecycle: how to subscribe to runtime events and integrate custom logic at each lifecycle stage.

```bash
python demo.py
```

**Expected output:**

```
{"timestamp": "...", "level": "INFO", "name": "AgentRuntime", "message": "Agent runtime starting."}
{"timestamp": "...", "level": "INFO", "name": "demo", "message": "Event listener: Runtime has started."}
{"timestamp": "...", "level": "INFO", "name": "demo", "message": "Event listener: Agent is about to run."}

--- Agent at work... ---
--- ...agent work complete. ---

{"timestamp": "...", "level": "INFO", "name": "demo", "message": "Event listener: Agent has finished running."}
{"timestamp": "...", "level": "INFO", "name": "AgentRuntime", "message": "Agent runtime stopped."}
{"timestamp": "...", "level": "INFO", "name": "demo", "message": "Event listener: Runtime has stopped."}
```

### Option C — Python API

Use the `build_agent` function directly in your own scripts.

```python
from pathlib import Path
from builders.build_agent import build_agent

# Build a runtime from any package directory
runtime = build_agent(Path("packages") / "research")

# Start the agent (fires the full event lifecycle)
runtime.start()
```

To run from a directory other than the repo root, adjust the path accordingly:

```python
from pathlib import Path
from builders.build_agent import build_agent

repo_root = Path("/absolute/path/to/agents")
runtime = build_agent(repo_root / "packages" / "research")
runtime.start()
```

---

## Creating a New Package

### 1. Generate the package scaffold

Run this Python snippet from the **root of the repository**. Replace `my_agent` and the field values with your own:

```python
from pathlib import Path
from builders.generate_package import generate_package

manifest = {
    "name": "My Agent",
    "version": "1.0.0",
    "inherits": "core",
    "description": "A short description of what this agent does.",
    "tools": ["filesystem"],        # list tools the agent needs
    "workflows": ["main_workflow"], # list workflow names
    "knowledge": ["domain_knowledge"],
    "entrypoint": {
        "workflow": "main_workflow" # must match an entry in the workflows list
    }
}

generate_package(Path("packages") / "my_agent", manifest)
print("Package created at packages/my_agent/agent.yaml")
```

This creates `packages/my_agent/agent.yaml`.

### 2. Register the package

```python
from pathlib import Path
from builders.register_package import register_package

entry = register_package(Path("packages") / "my_agent")
print(f"Registered: {entry}")
```

This validates the manifest and writes an entry to `registry/package_index.json`.

### 3. Run the new agent

```bash
python run_agent.py my_agent
```

**Expected output:**

```
Building agent from package: my_agent
Starting agent: My Agent
Agent finished.
```

---

## Running Tests

The full test suite uses `pytest`.

```bash
pytest
```

To run a specific test file:

```bash
pytest tests/test_runtime.py
```

To run all tests with verbose output:

```bash
pytest -v
```

**Current test status:**

| File | Tests |
|---|---|
| `test_interfaces.py` | 4 passed |
| `test_events.py` | 4 passed |
| `test_logging.py` | 2 passed |
| `test_runtime.py` | 3 passed |
| `test_tools.py` | 7 passed |
| `test_memory.py` | 6 passed |
| `test_orchestration.py` | 4 passed |
| `test_builders.py` | 6 passed |
| `test_validation.py` | 4 passed |
