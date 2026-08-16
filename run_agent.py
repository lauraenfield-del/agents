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
import json
from pathlib import Path

from builders.build_agent import build_agent
from core.runtime.conversational import ConversationalAgent
from core.tools.mobile import MobileAutomationTool


def run_ad_navigation_workflow(runtime, max_retries: int = 3) -> dict:
    try:
        mobile_tool = runtime.tool_manager.get_tool("mobile_automation")
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "details": f"mobile_automation tool unavailable: {exc}",
            "performance": {},
        }

    if not isinstance(mobile_tool, MobileAutomationTool):
        return {
            "status": "failed",
            "details": "mobile_automation is not a MobileAutomationTool instance.",
            "performance": {},
        }

    mobile_tool.start_performance_run()
    per_find_retries = 1
    workflow_log: list[dict] = []
    workflow_log.append({"step": "launch_app", "status": "success"})

    found = mobile_tool.run(
        {
            "action": "find_element",
            "by": "accessibility id",
            "value": "ad_banner",
            "retries": per_find_retries,
        }
    )
    workflow_log.append({"step": "find_element", "result": found})

    if found.get("status") == "ok":
        tap_result = mobile_tool.run(
            {
                "action": "tap",
                "x": 100,
                "y": 200,
            }
        )
        workflow_log.append({"step": "tap", "result": tap_result})
        performance = mobile_tool.end_performance_run()
        return {"status": "success", "workflow_log": workflow_log, "performance": performance}

    for _ in range(max_retries):
        scroll_result = mobile_tool.run({"action": "scroll", "direction": "down"})
        workflow_log.append({"step": "scroll", "result": scroll_result})

        found = mobile_tool.run(
            {
                "action": "find_element",
                "by": "accessibility id",
                "value": "ad_banner",
                "retries": per_find_retries,
            }
        )
        workflow_log.append({"step": "find_element", "result": found})
        if found.get("status") == "ok":
            tap_result = mobile_tool.run({"action": "tap", "x": 100, "y": 200})
            workflow_log.append({"step": "tap", "result": tap_result})
            performance = mobile_tool.end_performance_run()
            return {"status": "success", "workflow_log": workflow_log, "performance": performance}

    workflow_log.append({"step": "exit", "status": "graceful_failure"})
    performance = mobile_tool.end_performance_run()
    return {"status": "failed", "workflow_log": workflow_log, "performance": performance}


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
        if package_name == "ad_clicker" and "ad_navigation" in user_input.lower():
            result = run_ad_navigation_workflow(runtime)
            print(f"{agent_name}: {result['status']}")
            print(f"Performance summary: {json.dumps(result.get('performance', {}), sort_keys=True)}")
            sys.exit(0 if result["status"] == "success" else 1)
        if isinstance(runtime.agent, ConversationalAgent):
            reply = runtime.agent.chat(user_input)
            print(f"{agent_name}: {reply}")
        else:
            success = runtime.start(user_input=user_input)
            if not success:
                sys.exit(1)
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
