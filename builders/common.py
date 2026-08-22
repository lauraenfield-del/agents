from pathlib import Path

from core.packages.loader import PackageLoader


REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIRECTORY = REPO_ROOT / "packages"
REGISTRY_DIRECTORY = REPO_ROOT / "registry"


def get_package_loader() -> PackageLoader:
    return PackageLoader(str(PACKAGES_DIRECTORY), str(REGISTRY_DIRECTORY))
