from core.interfaces.agent import Agent
from core.events.bus import EventBus
from core.logging.logger import get_logger

class AgentRuntime:
    def __init__(self, agent: Agent, event_bus: EventBus):
        self.agent = agent
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)

    def start(self, *args, **kwargs):
        self.logger.info("Agent runtime starting.")
        self.event_bus.publish("runtime.start")

        try:
            self.event_bus.publish("agent.run.before")
            self.agent.run(*args, **kwargs)
            self.event_bus.publish("agent.run.after")
        except Exception as e:
            self.logger.exception(f"An error occurred during agent execution: {e}")
            self.event_bus.publish("agent.error", e)

        self.logger.info("Agent runtime stopped.")
        self.event_bus.publish("runtime.stop")
