import json

import pytest
from pathlib import Path

from core.packages.loader import PackageLoader, PackageValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = REPO_ROOT / "packages"
REGISTRY_DIR = REPO_ROOT / "registry"


def test_discover_packages():
    loader = PackageLoader(
        str(PACKAGES_DIR),
        str(REGISTRY_DIR),
    )
    packages = loader.discover_packages()
    assert "autonomous" in packages
    assert "research" in packages


def test_load_package_manifest():
    loader = PackageLoader(
        str(PACKAGES_DIR),
        str(REGISTRY_DIR),
    )
    manifest = loader.load_package("autonomous")
    assert manifest["name"] == "Autonomous Agent"
    assert manifest["entrypoint"]["workflow"] == "autonomous_controller"


def test_invalid_manifest_rejected():
    loader = PackageLoader(
        str(PACKAGES_DIR),
        str(REGISTRY_DIR),
    )
    with pytest.raises(PackageValidationError):
        loader.validate_manifest({"name": "bad"}, package_name="bad")


def test_registry_entries_load():
    loader = PackageLoader(
        str(PACKAGES_DIR),
        str(REGISTRY_DIR),
    )
    entries = loader.list_registry_entries()
    assert entries == {"agents": {}, "package_index": {}}


def test_build_runtime_config():
    loader = PackageLoader(
        str(PACKAGES_DIR),
        str(REGISTRY_DIR),
    )
    config = loader.build_runtime_config("research")
    assert config == {
        "package": "research",
        "name": "Research Agent",
        "description": "Research-focused agent for information gathering and analysis.",
        "tools": ["browser", "scraper"],
        "workflows": ["analysis", "reporting"],
        "knowledge": ["research_methodology"],
        "entrypoint": "research_controller",
    }
