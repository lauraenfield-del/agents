from __future__ import annotations

from typing import Any

from core.runtime.conversational import ConversationalAgent


class PersonalAssistantAgent(ConversationalAgent):
    """Conversational agent with approval-aware safeguards and status tracking."""

    _STATUS_KEY = "assistant:last_status"
    _PENDING_KEY = "assistant:pending_approvals"
    _WORKSPACE_KEY = "assistant:workspace"

    def chat(self, user_input: str) -> str:
        text = user_input.strip()
        if not text:
            return "Please share a task and I can start planning or executing it."

        if text.lower() in {"status", "progress", "what's done", "whats done"}:
            if self.memory is None:
                return "No status is available yet."
            state = self.memory.retrieve(self._STATUS_KEY) or {}
            if not state:
                return "No completed actions yet. I'm ready for your next task."
            return (
                f"Completed: {state.get('completed', 'none')} | "
                f"Pending approval: {state.get('pending_approval', 'none')} | "
                f"Next: {state.get('next_step', 'none')}"
            )

        response = super().chat(user_input)
        self._update_status_snapshot(response)
        return response

    def _build_action_prompt(self, user_input: str, transcript: list[dict[str, Any]]) -> str:
        base = super()._build_action_prompt(user_input, transcript)
        guardrails = (
            "\nSafety guardrails:\n"
            "1) Never request or store plaintext credentials in chat.\n"
            "2) Use secret_scope/secret_name references for integration tools.\n"
            "3) For high-risk actions, set approved=true only when user explicitly approved.\n"
            "4) If requirements are unclear, ask one concise clarifying question."
        )
        return base + guardrails

    def _execute_tool_calls(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, str]]:
        results = super()._execute_tool_calls(tool_calls)
        pending: list[dict[str, Any]] = []
        for call, result in zip(tool_calls, results):
            if result.get("status") == "requires_approval" or "requires_approval" in result.get("result", ""):
                pending.append({"tool": call["tool"], "args": call["args"]})

        if self.memory is not None and pending:
            self.memory.store(self._PENDING_KEY, pending)
        return results

    def _update_status_snapshot(self, response: str) -> None:
        if self.memory is None:
            return
        pending = self.memory.retrieve(self._PENDING_KEY) or []
        pending_summary = ", ".join(item.get("tool", "") for item in pending) if pending else "none"
        self.memory.store(
            self._STATUS_KEY,
            {
                "completed": "latest response generated",
                "pending_approval": pending_summary,
                "next_step": "await user direction or approval",
            },
        )
        self.memory.store(
            "assistant:last_response_redacted",
            {"redacted": True, "preview": "[redacted]", "length": len(response)},
        )
        self.refresh_workspace_snapshot()

    def refresh_workspace_snapshot(self) -> dict[str, Any] | None:
        if self.memory is None:
            return None
        snapshot = self.workspace_snapshot()
        self.memory.store(self._WORKSPACE_KEY, snapshot)
        return snapshot

    def workspace_snapshot(self) -> dict[str, Any]:
        status = self.memory.retrieve(self._STATUS_KEY) if self.memory is not None else {}
        pending = self.memory.retrieve(self._PENDING_KEY) if self.memory is not None else []
        manifest_value = getattr(self, "manifest", {})
        manifest = manifest_value if isinstance(manifest_value, dict) else {}
        frontend = manifest.get("frontend") if isinstance(manifest.get("frontend"), dict) else {}
        return {
            "assistant": {
                "name": getattr(self, "_name", "Personal Assistant"),
                "workflow": manifest.get("entrypoint", {}).get("workflow", "personal_assistant_controller"),
            },
            "status": status or {
                "completed": "none",
                "pending_approval": "none",
                "next_step": "ready for a task",
            },
            "pending_approvals": pending or [],
            "tools": self.tools.list_tools() if self.tools is not None else [],
            "connectors": frontend.get("connectors", [
                {"type": "chat_input", "entrypoint": "chat"},
                {"type": "workspace_snapshot", "source": self._WORKSPACE_KEY},
                {"type": "approval_queue", "source": self._PENDING_KEY},
            ]),
        }
