import json
from pathlib import Path

from builders.validate_package import validate_package


def register_package(
    package_dir: str | Path,
    registry_path: str | Path = Path("registry") / "package_index.json",
) -> dict:
    package_dir = Path(package_dir)
    manifest = validate_package(package_dir)
    registry_path = Path(registry_path)

    if registry_path.exists():
        with registry_path.open("r", encoding="utf-8") as registry_file:
            registry = json.load(registry_file) or {}
    else:
        registry = {}

    registry[package_dir.name] = {
        "name": manifest["name"],
        "version": manifest["version"],
        "description": manifest["description"],
        "path": str(package_dir.as_posix()),
        "entrypoint": manifest["entrypoint"]["workflow"],
    }

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", encoding="utf-8") as registry_file:
        json.dump(registry, registry_file, indent=2, sort_keys=True)

    return registry[package_dir.name]