from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from core.runtime.conversational import ConversationalAgent


class PersonalAssistantAgent(ConversationalAgent):
    """Conversational agent with approval-aware safeguards and status tracking."""

    _STATUS_KEY = "assistant:last_status"
    _PENDING_KEY = "assistant:pending_approvals"
    _WORKSPACE_KEY = "assistant:workspace"
    _APPROVAL_ACTIONS = {
        ("sendblue", "send_message"),
        ("shopify", "update_product"),
        ("canva", "update_design"),
        ("canva", "export_design"),
    }
    _APPROVAL_RE = re.compile(r"^approve(?:\s+token)?\s+([a-f0-9]{12})$", re.IGNORECASE)

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

        approval_response = self._handle_approval(text)
        if approval_response is not None:
            self._update_status_snapshot(approval_response)
            return approval_response

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
        assert self.tools is not None
        results: list[dict[str, str]] = []
        pending: list[dict[str, Any]] = []
        known_tools = set(self.tools.list_tools())

        for call in tool_calls:
            tool_name = call["tool"]
            args = dict(call["args"])
            if tool_name not in known_tools:
                results.append({"tool": tool_name, "result": "Error: unknown tool"})
                continue
            if self._requires_approval(tool_name, args):
                args.pop("approved", None)
                token = self._approval_token(tool_name, args)
                pending.append({"tool": tool_name, "args": args, "approval_token": token})
                results.append(
                    {
                        "tool": tool_name,
                        "status": "requires_approval",
                        "result": f"Approval required. Ask the user to send 'approve {token}' to continue.",
                    }
                )
                continue
            try:
                result = self.tools.execute_tool(tool_name, **args)
                result_text = str(result)
                status = result.get("status") if isinstance(result, dict) else ""
                results.append({"tool": tool_name, "status": status or "", "result": result_text})
            except Exception as exc:  # noqa: BLE001
                results.append({"tool": tool_name, "result": f"Error: {exc}"})

        if self.memory is not None:
            self.memory.store(self._PENDING_KEY, pending)
        return results

    def _handle_approval(self, user_input: str) -> str | None:
        if self.memory is None:
            return None
        match = self._APPROVAL_RE.fullmatch(user_input)
        if match is None:
            return None
        pending = self.memory.retrieve(self._PENDING_KEY) or []
        token = match.group(1).lower()
        for index, item in enumerate(pending):
            if item.get("approval_token") != token:
                continue
            if self.tools is None:
                return "Unable to execute the approved request because no tools are available."
            args = dict(item.get("args", {}))
            args["approved"] = True
            try:
                result = self.tools.execute_tool(item["tool"], **args)
            except Exception as exc:  # noqa: BLE001
                return f"Approved action failed: {exc}"
            remaining = pending[:index] + pending[index + 1 :]
            self.memory.store(self._PENDING_KEY, remaining)
            return f"Approved action completed for {item['tool']}: {result}"
        return "No matching approval request was found."

    @classmethod
    def _requires_approval(cls, tool_name: str, args: dict[str, Any]) -> bool:
        action = args.get("action")
        return isinstance(action, str) and (tool_name, action) in cls._APPROVAL_ACTIONS

    @staticmethod
    def _approval_token(tool_name: str, args: dict[str, Any]) -> str:
        payload = json.dumps({"tool": tool_name, "args": args}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

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
