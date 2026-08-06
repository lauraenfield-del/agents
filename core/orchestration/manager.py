from typing import Dict
from core.interfaces.agent import Workflow, Agent

class WorkflowManager:
    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}

    def register_workflow(self, workflow: Workflow):
        if not isinstance(workflow, Workflow):
            raise TypeError("Workflow must be an instance of the Workflow interface.")
        self._workflows[workflow.name] = workflow

    def run_workflow(self, name: str, agent: Agent):
        if name not in self._workflows:
            raise ValueError(f"Workflow '{name}' not found.")
        self._workflows[name].run(agent)
