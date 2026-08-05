import argparse
import json

from builders.common import get_package_loader


def main():
    parser = argparse.ArgumentParser(description="Validate agent package manifests.")
    parser.add_argument("package", nargs="?", help="Optional package name to validate.")
    args = parser.parse_args()

    loader = get_package_loader()
    package_names = [args.package] if args.package else loader.discover_packages()

    results = {}
    for package_name in package_names:
        loader.load_package(package_name)
        results[package_name] = "valid"

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()