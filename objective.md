# Agent Framework Objective

This repository's current objective is narrower than a full "agent operating system":

- keep the Python runtime in `core/` generic
- define agent variants through package manifests in `packages/`
- build runnable agents through `builders/build_agent.py`
- keep the registry in `registry/package_index.json` as the package source of truth

## Current architectural boundary

An executable agent in this repository is currently:

```text
package manifest
    +
core runtime
    +
registered built-in tools
    +
memory + model wiring
    =
runnable AgentRuntime
```

The repository does **not** currently implement the larger aspirational structures that were previously documented here, such as `shared/`, `specialty/`, or package-local prompt/workflow/tool directories.

## Principles that match the current codebase

### 1. Core runtime stays reusable

`core/` holds the shared runtime concerns:

- lifecycle events
- runtime execution
- tool registration and execution
- memory implementations
- model adapters
- validation
- orchestration helpers

Package-specific behavior should not be added directly to `core/`.

### 2. Packages are manifest-driven

Each package is currently represented by a single `agent.yaml` file under `packages/<name>/`.

That manifest declares:

- package metadata
- tool names
- workflow labels
- knowledge labels
- entrypoint workflow name

The runtime currently uses those manifests to assemble a `ManifestAgent`.

### 3. Builders are the integration layer

`builders/` is responsible for:

- validating manifests
- generating new manifests
- registering packages in the JSON registry
- creating an `AgentRuntime` from a package directory

### 4. Registry remains explicit

`registry/package_index.json` is the current catalog of registered packages.

`registry/agents.json` exists in the repository but is not currently used as an active runtime source.

## Current lifecycle

The runtime path implemented today is:

```text
1. Load and validate package manifest
2. Register known built-in tools from the manifest
3. Create memory
4. Select a model provider or fall back to MockModel
5. Construct AgentRuntime
6. Run agent logic through runtime.start(...)
```

## Current package inventory

The repository currently includes these packages:

- autonomous
- coding
- customer_support
- marketing
- research
- social_media

## Non-runtime repository content

The repo also contains `skills/`, which is versioned content adjacent to the framework but is not part of the manifest-driven Python runtime.
