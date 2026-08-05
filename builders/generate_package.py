from pathlib import Path

import yaml


def generate_package(package_dir: str | Path, manifest: dict) -> Path:
    package_dir = Path(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = package_dir / "agent.yaml"
    with manifest_path.open("w", encoding="utf-8") as manifest_file:
        yaml.safe_dump(manifest, manifest_file, sort_keys=False)

    return manifest_path