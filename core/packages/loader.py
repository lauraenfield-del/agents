import json
from pathlib import Path
from typing import Any, Dict, List


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
        manifest_path = self.packages_directory / package_name / "agent.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Package manifest not found: {manifest_path}")
        manifest = self._parse_simple_yaml(manifest_path)
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

    def _parse_simple_yaml(self, path: Path) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        current_list_key = None
        current_dict_key = None

        with path.open("r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.rstrip()
                if not line.strip():
                    continue

                stripped = line.strip()
                if stripped.startswith("- "):
                    if current_list_key is None:
                        raise PackageValidationError(f"List item found before list key in {path}")
                    result[current_list_key].append(stripped[2:].strip())
                    continue

                indent = len(line) - len(line.lstrip(" "))
                if ":" not in stripped:
                    raise PackageValidationError(f"Unsupported manifest line '{line}' in {path}")

                key, value = stripped.split(":", 1)
                value = value.strip()

                if indent == 0 and value:
                    current_list_key = None
                    current_dict_key = None
                    result[key] = value
                elif indent == 0 and not value and key in ("tools", "workflows", "knowledge"):
                    current_dict_key = None
                    current_list_key = key
                    result[key] = []
                elif indent == 0 and not value:
                    current_list_key = None
                    result[key] = {}
                    current_dict_key = key
                elif indent == 2 and current_dict_key:
                    result[current_dict_key][key] = value
                else:
                    raise PackageValidationError(f"Unsupported indentation structure in {path}: '{line}'")

        for key in ("tools", "workflows", "knowledge"):
            result.setdefault(key, [])
        return result
