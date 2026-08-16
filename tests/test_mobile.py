import json
import time
from types import SimpleNamespace

from core.tools.manager import ToolManager
from core.tools.mobile import MobileAutomationTool
from run_agent import run_ad_navigation_workflow


class ElementNotFound(Exception):
    pass


class FakeElement:
    def __init__(self, element_id: str = "el-1") -> None:
        self.id = element_id


class TapFailDriver:
    def __init__(self, fail_count: int) -> None:
        self.fail_count = fail_count
        self.tap_calls = 0

    def tap(self, _points):
        self.tap_calls += 1
        if self.tap_calls <= self.fail_count:
            raise ElementNotFound("ElementNotFound")


class TimeoutDriver:
    def find_element(self, _by, _value):
        time.sleep(0.05)
        return FakeElement()


class FindFailDriver:
    def tap(self, _points):
        return None

    def find_element(self, _by, _value):
        raise ElementNotFound("ElementNotFound")


class BranchDriver:
    def __init__(self, success_after_finds: int | None) -> None:
        self.success_after_finds = success_after_finds
        self.find_calls = 0
        self.scroll_calls = 0
        self.tap_calls = 0

    def get_window_size(self):
        return {"width": 300, "height": 600}

    def execute_script(self, _script, _payload):
        self.scroll_calls += 1

    def find_element(self, _by, _value):
        self.find_calls += 1
        if self.success_after_finds is not None and self.find_calls >= self.success_after_finds:
            return FakeElement("ad-1")
        raise ElementNotFound("ElementNotFound")

    def tap(self, _points):
        self.tap_calls += 1


def _runtime_with_mobile_tool(driver) -> SimpleNamespace:
    tool_manager = ToolManager()
    tool_manager.register_tool(MobileAutomationTool(driver=driver))
    return SimpleNamespace(tool_manager=tool_manager)


def test_mobile_run_accepts_json_and_retries_with_structured_fail_log(monkeypatch):
    driver = TapFailDriver(fail_count=3)
    tool = MobileAutomationTool(driver=driver)
    captured_logs: list[str] = []
    monkeypatch.setattr(tool._logger, "error", lambda msg: captured_logs.append(msg))

    result = tool.run(json.dumps({"action": "tap", "x": 1, "y": 2, "retries": 3, "timeout_seconds": 1}))

    assert result["status"] == "failed"
    assert result["attempts"] == 3
    assert result["error"] == "ElementNotFound"
    assert captured_logs
    payload = json.loads(captured_logs[-1])
    assert payload == {"action": "tap", "status": "failed", "error": "ElementNotFound"}


def test_mobile_timeout_is_reported_as_error():
    tool = MobileAutomationTool(driver=TimeoutDriver())

    result = tool.run(
        {
            "action": "find_element",
            "by": "accessibility id",
            "value": "ad_banner",
            "retries": 1,
            "timeout_seconds": 0.01,
        }
    )

    assert result["status"] == "failed"
    assert result["error"] == "TimeoutError"


def test_performance_metrics_logging_tracks_success_failure_and_errors():
    driver = FindFailDriver()
    tool = MobileAutomationTool(driver=driver)
    tool.start_performance_run()

    tap_result = tool.run({"action": "tap", "x": 1, "y": 2, "retries": 1})
    assert tap_result["status"] == "ok"

    find_result = tool.run(
        {
            "action": "find_element",
            "by": "accessibility id",
            "value": "missing",
            "retries": 1,
        }
    )
    assert find_result["status"] == "failed"

    report = tool.end_performance_run()
    assert report["success_count"] == 1
    assert report["failure_count"] == 1
    assert report["avg_latency"] >= 0
    assert report["error_types"]["ElementNotFound"] == 1
    assert isinstance(report["json"], str)


def test_ad_navigation_workflow_success_branch():
    runtime = _runtime_with_mobile_tool(BranchDriver(success_after_finds=2))

    result = run_ad_navigation_workflow(runtime, max_retries=3)

    assert result["status"] == "success"
    steps = [entry["step"] for entry in result["workflow_log"]]
    assert "tap" in steps


def test_ad_navigation_workflow_failure_branch_exits_gracefully():
    runtime = _runtime_with_mobile_tool(BranchDriver(success_after_finds=None))

    result = run_ad_navigation_workflow(runtime, max_retries=3)

    assert result["status"] == "failed"
    assert result["workflow_log"][-1] == {"step": "exit", "status": "graceful_failure"}
