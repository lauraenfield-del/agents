from __future__ import annotations

import json
from typing import Any

from core.interfaces.agent import Tool


class MobileAutomationTool(Tool):
    """Wraps basic Appium actions for mobile automation."""

    def __init__(self, driver: Any | None = None) -> None:
        self._driver = driver

    @property
    def name(self) -> str:
        return "mobile_automation"

    @property
    def description(self) -> str:
        return "Run Appium-backed mobile actions like tap, scroll, and find_element."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["tap", "scroll", "find_element"]},
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "left": {"type": "integer"},
                "top": {"type": "integer"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "percent": {"type": "number", "minimum": 0.01, "maximum": 1.0},
                "by": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    def run(self, payload: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload, str):
            try:
                command = json.loads(payload)
            except json.JSONDecodeError as exc:
                return {"status": "error", "details": f"Invalid JSON payload: {exc}"}
        elif isinstance(payload, dict):
            command = payload
        else:
            return {"status": "error", "details": "Payload must be a JSON string or object."}

        action = command.get("action")
        if not isinstance(action, str) or not action:
            return {"status": "error", "details": "Payload must include a non-empty 'action'."}

        return self.execute(
            action=action,
            x=command.get("x"),
            y=command.get("y"),
            left=command.get("left"),
            top=command.get("top"),
            width=command.get("width"),
            height=command.get("height"),
            direction=command.get("direction", "down"),
            percent=command.get("percent", 0.6),
            by=command.get("by"),
            value=command.get("value"),
        )

    def execute(
        self,
        action: str,
        x: int | None = None,
        y: int | None = None,
        left: int = 0,
        top: int = 0,
        width: int | None = None,
        height: int | None = None,
        direction: str = "down",
        percent: float = 0.6,
        by: str | None = None,
        value: str | None = None,
    ) -> dict[str, Any]:
        if self._driver is None:
            return {"status": "error", "details": "No Appium driver attached to mobile_automation."}

        if action == "tap":
            if x is None or y is None:
                return {"status": "error", "details": "tap requires integer coordinates: x and y."}
            return self._tap(x, y)

        if action == "scroll":
            return self._scroll(left, top, width, height, direction, percent)

        if action == "find_element":
            if not by or not value:
                return {"status": "error", "details": "find_element requires both 'by' and 'value'."}
            return self._find_element(by, value)

        return {"status": "error", "details": f"Unsupported mobile action: {action}."}

    def _tap(self, x: int, y: int) -> dict[str, Any]:
        try:
            if hasattr(self._driver, "tap"):
                self._driver.tap([(x, y)])
            else:
                self._driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
            return {"status": "ok", "action": "tap", "x": x, "y": y}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "action": "tap", "details": str(exc)}

    def _scroll(
        self,
        left: int,
        top: int,
        width: int | None,
        height: int | None,
        direction: str,
        percent: float,
    ) -> dict[str, Any]:
        try:
            viewport = self._driver.get_window_size() if hasattr(self._driver, "get_window_size") else {}
            viewport_width = int(viewport.get("width", 1080))
            viewport_height = int(viewport.get("height", 1920))
            scroll_width = width if width is not None else viewport_width
            scroll_height = height if height is not None else viewport_height
            self._driver.execute_script(
                "mobile: scrollGesture",
                {
                    "left": left,
                    "top": top,
                    "width": scroll_width,
                    "height": scroll_height,
                    "direction": direction,
                    "percent": percent,
                },
            )
            return {"status": "ok", "action": "scroll", "direction": direction}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "action": "scroll", "details": str(exc)}

    def _find_element(self, by: str, value: str) -> dict[str, Any]:
        try:
            element = self._driver.find_element(by, value)
            element_id = getattr(element, "id", None)
            return {
                "status": "ok",
                "action": "find_element",
                "found": True,
                "by": by,
                "value": value,
                "element_id": element_id,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "action": "find_element",
                "found": False,
                "by": by,
                "value": value,
                "details": str(exc),
            }
