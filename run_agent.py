import sys
from pathlib import Path

from builders.build_agent import build_agent

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py <package_name> [user_input]")
        sys.exit(1)

    package_name = sys.argv[1]
    user_input = " ".join(sys.argv[2:]).strip()
    if not user_input:
        user_input = input("Enter your request: ").strip()

    if not user_input:
        print("Error: a non-empty request is required.")
        sys.exit(1)

    package_dir = Path("packages") / package_name

    if not package_dir.is_dir():
        print(f"Error: Package '{package_name}' not found at {package_dir}")
        sys.exit(1)

    print(f"Building agent from package: {package_name}")
    runtime = build_agent(package_dir)

    print(f"Starting agent: {runtime.agent.manifest['name']}")
    result = runtime.start(user_input=user_input, raise_exceptions=True)
    print(f"Agent finished with result: {result}")
