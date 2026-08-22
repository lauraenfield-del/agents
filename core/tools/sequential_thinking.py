from core.interfaces.agent import Tool


class SequentialThinkingTool(Tool):
    def __init__(self):
        self._sessions: dict[str, list[str]] = {}

    @property
    def name(self) -> str:
        return "sequential_thinking"

    @property
    def description(self) -> str:
        return "Tracks step-by-step reasoning notes for a task session."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "thought": {"type": "string"},
                "operation": {"type": "string", "enum": ["append", "list", "clear"]},
            },
            "required": ["session_id", "operation"],
            "additionalProperties": False,
        }

    def execute(self, session_id: str, operation: str, thought: str | None = None):
        if operation == "append":
            if not thought:
                raise ValueError("thought is required for append operation")
            self._sessions.setdefault(session_id, []).append(thought)
            return {"session_id": session_id, "steps": self._sessions[session_id]}

        if operation == "list":
            return {"session_id": session_id, "steps": self._sessions.get(session_id, [])}

        if operation == "clear":
            self._sessions.pop(session_id, None)
            return {"session_id": session_id, "steps": []}

        raise ValueError(f"Unsupported operation: {operation}")
