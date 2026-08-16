from __future__ import annotations

import json
import threading
import time
from typing import Any

from core.interfaces.agent import Tool
from core.logging.logger import get_logger
from core.performance import PerformanceLogger


class MobileAutomationTool(Tool):
    """Wraps basic Appium actions for mobile automation."""

    def __init__(
        self,
        driver: Any | None = None,
        performance_logger: PerformanceLogger | None = None,
    ) -> None:
        self._driver = driver
        self.performance_logger = performance_logger or PerformanceLogger()
        self._logger = get_logger(self.__class__.__name__)

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
                "retries": {"type": "integer", "minimum": 1, "maximum": 10},
                "timeout_seconds": {"type": "number", "minimum": 0.1, "maximum": 60},
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
            retries=command.get("retries", 3),
            timeout_seconds=command.get("timeout_seconds", 5),
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
        retries: int = 3,
        timeout_seconds: float = 5,
    ) -> dict[str, Any]:
        if self._driver is None:
            return {"status": "error", "details": "No Appium driver attached to mobile_automation."}

        if action == "tap":
            if x is None or y is None:
                return {"status": "error", "details": "tap requires integer coordinates: x and y."}
            return self._execute_with_retries(
                action="tap",
                action_func=lambda: self._tap(x, y),
                retries=retries,
                timeout_seconds=timeout_seconds,
            )

        if action == "scroll":
            return self._execute_with_retries(
                action="scroll",
                action_func=lambda: self._scroll(left, top, width, height, direction, percent),
                retries=retries,
                timeout_seconds=timeout_seconds,
            )

        if action == "find_element":
            if not by or not value:
                return {"status": "error", "details": "find_element requires both 'by' and 'value'."}
            return self._execute_with_retries(
                action="find_element",
                action_func=lambda: self._find_element(by, value),
                retries=retries,
                timeout_seconds=timeout_seconds,
            )

        return {"status": "error", "details": f"Unsupported mobile action: {action}."}

    def start_performance_run(self) -> None:
        self.performance_logger.start_run()

    def end_performance_run(self) -> dict[str, Any]:
        return self.performance_logger.end_run()

    def _execute_with_retries(
        self,
        action: str,
        action_func: Any,
        retries: int,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        max_retries = max(1, int(retries))
        total_latency = 0.0

        for attempt in range(1, max_retries + 1):
            started_at = time.perf_counter()
            try:
                result = self._run_with_timeout(action_func, timeout_seconds)
                latency = time.perf_counter() - started_at
                total_latency += latency
                self.performance_logger.log_action(action=action, status="success", latency=latency)
                if isinstance(result, dict):
                    result.setdefault("action", action)
                    result["attempts"] = attempt
                    result["latency"] = total_latency
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                latency = time.perf_counter() - started_at
                total_latency += latency
                error_type = exc.__class__.__name__
                self._logger.error(
                    json.dumps(
                        {
                            "action": action,
                            "status": "failed",
                            "error": error_type,
                        },
                        sort_keys=True,
                    )
                )

        assert last_error is not None
        self.performance_logger.log_action(
            action=action,
            status="failed",
            latency=total_latency,
            error=last_error.__class__.__name__,
        )
        return {
            "status": "failed",
            "action": action,
            "error": last_error.__class__.__name__,
            "details": str(last_error),
            "attempts": max_retries,
        }

    @staticmethod
    def _run_with_timeout(action_func: Any, timeout_seconds: float) -> Any:
        result_holder: dict[str, Any] = {}
        error_holder: dict[str, Exception] = {}

        def _target() -> None:
            try:
                result_holder["result"] = action_func()
            except Exception as exc:  # noqa: BLE001
                error_holder["error"] = exc

        worker = threading.Thread(target=_target, daemon=True)
        worker.start()
        worker.join(timeout_seconds)
        if worker.is_alive():
            raise TimeoutError(f"Action timed out after {timeout_seconds} seconds.")
        if "error" in error_holder:
            raise error_holder["error"]
        return result_holder.get("result")

    def _tap(self, x: int, y: int) -> dict[str, Any]:
        if hasattr(self._driver, "tap"):
            self._driver.tap([(x, y)])
        else:
            self._driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
        return {"status": "ok", "action": "tap", "x": x, "y": y}

    def _scroll(
        self,
        left: int,
        top: int,
        width: int | None,
        height: int | None,
        direction: str,
        percent: float,
    ) -> dict[str, Any]:
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

    def _find_element(self, by: str, value: str) -> dict[str, Any]:
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
