import time
from core.interfaces.agent import Agent
from core.events.bus import EventBus
from core.runtime.agent import AgentRuntime
from core.logging.logger import get_logger

# 1. Create a basic agent
class DemoAgent(Agent):
    def run(self, *args, **kwargs):
        print("\n--- Agent at work... ---")
        time.sleep(2)
        print("--- ...agent work complete. ---\n")

# 2. Initialize the EventBus and a logger
event_bus = EventBus()
logger = get_logger("demo")

# 3. Set up event listeners
def on_runtime_start():
    logger.info("Event listener: Runtime has started.")

def on_agent_run_before():
    logger.info("Event listener: Agent is about to run.")

def on_agent_run_after():
    logger.info("Event listener: Agent has finished running.")

def on_runtime_stop():
    logger.info("Event listener: Runtime has stopped.")

event_bus.subscribe("runtime.start", on_runtime_start)
event_bus.subscribe("agent.run.before", on_agent_run_before)
event_bus.subscribe("agent.run.after", on_agent_run_after)
event_bus.subscribe("runtime.stop", on_runtime_stop)

# 4. Initialize the AgentRuntime
agent = DemoAgent()
runtime = AgentRuntime(agent=agent, event_bus=event_bus)

# 5. Start the runtime
if __name__ == "__main__":
    runtime.start()
