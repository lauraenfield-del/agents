"""run_agent.py – Launch an agent package from the command line.

Usage
-----
    python run_agent.py <package_name> [message]

If *message* is provided the agent responds once and exits.
If omitted an interactive REPL starts (type 'exit' or 'quit' to stop).

Examples
--------
    python run_agent.py autonomous
    python run_agent.py research "What is quantum computing?"
"""
import sys
from pathlib import Path

from builders.build_agent import build_agent
from core.runtime.conversational import ConversationalAgent


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    package_name = sys.argv[1]
    package_dir = Path("packages") / package_name

    if not package_dir.is_dir():
        print(f"Error: Package '{package_name}' not found at {package_dir}")
        sys.exit(1)

    print(f"Building agent from package: {package_name}")
    runtime = build_agent(package_dir)
    agent_name = runtime.agent.manifest["name"]
    print(f"Agent ready: {agent_name}\n")

    # Single-shot mode: message passed on the command line
    if len(sys.argv) >= 3:
        user_input = " ".join(sys.argv[2:])
        if isinstance(runtime.agent, ConversationalAgent):
            reply = runtime.agent.chat(user_input)
            print(f"{agent_name}: {reply}")
        else:
            runtime.start(user_input=user_input)
        sys.exit(0)

    # Interactive REPL mode
    print(f"Chatting with {agent_name}. Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if not user_input:
            continue

        if isinstance(runtime.agent, ConversationalAgent):
            reply = runtime.agent.chat(user_input)
            print(f"{agent_name}: {reply}\n")
        else:
            runtime.start(user_input=user_input)

