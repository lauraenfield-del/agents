from typing import List, Dict, Any
from core.interfaces.agent import Workflow, Agent

class SequentialWorkflow(Workflow):
    def __init__(self, name: str, steps: List[Dict[str, Any]]):
        self._name = name
        self.steps = steps

    @property
    def name(self) -> str:
        return self._name

    def run(self, agent: Agent):
        for step in self.steps:
            if "tool_call" in step:
                tool_name = step["tool_call"]["name"]
                tool_args = step["tool_call"].get("args", {})
                agent.tools.execute_tool(tool_name, **tool_args)
            elif "prompt" in step:
                agent.model.generate(step["prompt"])
