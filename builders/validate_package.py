from pathlib import Path

import yaml


REQUIRED_KEYS = {
    "name": str,
    "version": str,
    "inherits": str,
    "description": str,
    "tools": list,
    "workflows": list,
    "knowledge": list,
    "entrypoint": dict,
}


def load_package_manifest(package_dir: str | Path) -> dict:
    manifest_path = Path(package_dir) / "agent.yaml"
    if not manifest_path.exists():
        raise ValueError(f"Package manifest not found at expected path: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        data = yaml.safe_load(manifest_file) or {}
    if not isinstance(data, dict):
        raise ValueError("Package manifest must deserialize to a mapping.")
    return data


def validate_package(package_dir: str | Path) -> dict:
    manifest = load_package_manifest(package_dir)

    for key, expected_type in REQUIRED_KEYS.items():
        if key not in manifest:
            raise ValueError(f"Package manifest missing required field: {key}")
        if not isinstance(manifest[key], expected_type):
            raise ValueError(
                f"Package manifest field '{key}' must be of type {expected_type.__name__}"
            )

    workflow = manifest["entrypoint"].get("workflow")
    if not isinstance(workflow, str) or not workflow:
        raise ValueError("Package manifest entrypoint.workflow must be a non-empty string")

    for list_field in ("tools", "workflows", "knowledge"):
        for i, item in enumerate(manifest[list_field]):
            if not isinstance(item, str):
                raise ValueError(
                    f"Package manifest field '{list_field}[{i}]' must be a string, got {type(item).__name__}"
                )

    return manifest