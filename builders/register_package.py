import argparse
import json

from builders.common import REGISTRY_DIRECTORY, get_package_loader


def main():
    parser = argparse.ArgumentParser(description="Register validated packages in the registry.")
    parser.add_argument("package", nargs="?", help="Optional package name to register.")
    args = parser.parse_args()

    loader = get_package_loader()
    package_names = [args.package] if args.package else loader.discover_packages()
    entries = {}

    for package_name in package_names:
        manifest = loader.load_package(package_name)
        entries[package_name] = {
            "name": manifest["name"],
            "version": manifest["version"],
            "description": manifest["description"],
            "entrypoint": manifest["entrypoint"]["workflow"],
        }

    agents_path = REGISTRY_DIRECTORY / "agents.json"
    index_path = REGISTRY_DIRECTORY / "package_index.json"

    agents_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    index_path.write_text(json.dumps({"packages": sorted(entries.keys())}, indent=2), encoding="utf-8")

    print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()