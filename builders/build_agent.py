import argparse
import json

from builders.common import get_package_loader


def main():
    parser = argparse.ArgumentParser(description="Build runtime configuration for an agent package.")
    parser.add_argument("package", help="Package name to build.")
    args = parser.parse_args()

    loader = get_package_loader()
    runtime_config = loader.build_runtime_config(args.package)
    print(json.dumps(runtime_config, indent=2))


if __name__ == "__main__":
    main()