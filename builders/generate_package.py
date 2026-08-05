import argparse
from pathlib import Path

from builders.common import PACKAGES_DIRECTORY


MANIFEST_TEMPLATE = """name: {display_name}
version: 1.0.0
inherits: core
description: {description}
tools:
  - filesystem
workflows:
  - default_workflow
knowledge:
  - default_knowledge
entrypoint:
  workflow: default_workflow
"""


def main():
    parser = argparse.ArgumentParser(description="Generate a new agent package skeleton.")
    parser.add_argument("package", help="Directory name for the package.")
    parser.add_argument("--name", dest="display_name", help="Human-readable package name.")
    parser.add_argument("--description", default="Generated agent package.", help="Package description.")
    args = parser.parse_args()

    package_dir = PACKAGES_DIRECTORY / args.package
    package_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = package_dir / "agent.yaml"
    if not manifest_path.exists():
        manifest_path.write_text(
            MANIFEST_TEMPLATE.format(
                display_name=args.display_name or args.package.replace("_", " ").title(),
                description=args.description,
            ),
            encoding="utf-8",
        )

    for child in ("prompts", "workflows", "tools", "knowledge", "policies", "config", "assets", "overrides"):
        (package_dir / child).mkdir(exist_ok=True)

    print(str(package_dir))


if __name__ == "__main__":
    main()