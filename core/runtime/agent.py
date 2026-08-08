from core.interfaces.agent import Agent, Memory, Model
from core.events.bus import EventBus
from core.logging.logger import get_logger
from core.tools.manager import ToolManager

class AgentRuntime:
    def __init__(self, agent: Agent, event_bus: EventBus, tool_manager: ToolManager, memory: Memory, model: Model):
        self.agent = agent
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)
        self.tool_manager = tool_manager
        self.memory = memory
        self.model = model

        # Provide the agent with access to tools, memory, and model
        self.agent.tools = self.tool_manager
        self.agent.memory = self.memory
        self.agent.model = self.model

    def start(self, *args, **kwargs):
        self.logger.info("Agent runtime starting.")
        self.event_bus.publish("runtime.start")

        success = False
        try:
            self.event_bus.publish("agent.run.before")
            self.agent.run(*args, **kwargs)
            self.event_bus.publish("agent.run.after")
            success = True
        except Exception as e:
            self.logger.exception(f"An error occurred during agent execution: {e}")
            self.event_bus.publish("agent.error", e)

        self.logger.info("Agent runtime stopped.")
        self.event_bus.publish("runtime.stop")
        return success
