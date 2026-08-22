import json
from pathlib import Path
from typing import Any, Dict, List

import yaml


class PackageValidationError(ValueError):
    pass


class PackageLoader:
    REQUIRED_FIELDS = {
        "name": str,
        "version": str,
        "inherits": str,
        "description": str,
        "tools": list,
        "workflows": list,
        "knowledge": list,
        "entrypoint": dict,
    }

    def __init__(self, packages_directory: str, registry_directory: str):
        self.packages_directory = Path(packages_directory)
        self.registry_directory = Path(registry_directory)

    def discover_packages(self) -> List[str]:
        if not self.packages_directory.exists():
            return []
        return sorted(
            package_dir.name
            for package_dir in self.packages_directory.iterdir()
            if package_dir.is_dir() and (package_dir / "agent.yaml").exists()
        )

    def load_package(self, package_name: str) -> Dict[str, Any]:
        manifest_path = (self.packages_directory / package_name / "agent.yaml").resolve()
        try:
            manifest_path.relative_to(self.packages_directory.resolve())
        except ValueError as error:
            raise PackageValidationError(
                f"Package '{package_name}' resolves outside the packages directory."
            ) from error
        if not manifest_path.exists():
            raise FileNotFoundError(f"Package manifest not found: {manifest_path}")
        manifest = self._load_yaml_manifest(manifest_path)
        self.validate_manifest(manifest, package_name=package_name)
        return manifest

    def validate_manifest(self, manifest: Dict[str, Any], package_name: str | None = None) -> None:
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in manifest:
                raise PackageValidationError(f"Missing required field '{field}' in package '{package_name or manifest.get('name', 'unknown')}'.")
            if not isinstance(manifest[field], expected_type):
                raise PackageValidationError(
                    f"Field '{field}' in package '{package_name or manifest.get('name', 'unknown')}' must be of type {expected_type.__name__}."
                )

        if manifest["inherits"] != "core":
            raise PackageValidationError("Only packages inheriting from 'core' are currently supported.")

        for list_field in ("tools", "workflows", "knowledge"):
            if not all(isinstance(item, str) and item.strip() for item in manifest[list_field]):
                raise PackageValidationError(f"Field '{list_field}' must contain only non-empty strings.")

        entrypoint = manifest["entrypoint"]
        if "workflow" not in entrypoint or not isinstance(entrypoint["workflow"], str) or not entrypoint["workflow"].strip():
            raise PackageValidationError("Entrypoint must define a non-empty 'workflow' value.")

    def list_registry_entries(self) -> Dict[str, Any]:
        agents_path = self.registry_directory / "agents.json"
        index_path = self.registry_directory / "package_index.json"
        return {
            "agents": self._load_json(agents_path),
            "package_index": self._load_json(index_path),
        }

    def build_runtime_config(self, package_name: str) -> Dict[str, Any]:
        manifest = self.load_package(package_name)
        return {
            "package": package_name,
            "name": manifest["name"],
            "description": manifest["description"],
            "tools": manifest["tools"],
            "workflows": manifest["workflows"],
            "knowledge": manifest["knowledge"],
            "entrypoint": manifest["entrypoint"]["workflow"],
        }

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as file:
            content = file.read().strip()
        return json.loads(content) if content else {}

    def _load_yaml_manifest(self, path: Path) -> Dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except yaml.YAMLError as error:
            raise PackageValidationError(f"Invalid YAML in package manifest {path}: {error}") from error

        if not isinstance(data, dict):
            raise PackageValidationError(f"Package manifest {path} must contain a YAML mapping at the top level.")

        return data
