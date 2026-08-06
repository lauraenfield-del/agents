import sys
from pathlib import Path
from builders.build_agent import build_agent

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py <package_name>")
        sys.exit(1)

    package_name = sys.argv[1]
    package_dir = Path("packages") / package_name

    if not package_dir.is_dir():
        print(f"Error: Package '{package_name}' not found at {package_dir}")
        sys.exit(1)

    print(f"Building agent from package: {package_name}")
    runtime = build_agent(package_dir)

    print(f"Starting agent: {runtime.agent.manifest['name']}")
    runtime.start()
    print("Agent finished.")
