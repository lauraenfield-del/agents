import pytest
from core.events.bus import EventBus

def test_subscribe_and_publish():
    bus = EventBus()
    test_data = {"called": False}

    def handler(data):
        data["called"] = True

    bus.subscribe("test_event", handler)
    bus.publish("test_event", test_data)

    assert test_data["called"] is True

def test_publish_with_no_subscribers():
    bus = EventBus()
    try:
        bus.publish("non_existent_event")
    except Exception as e:
        pytest.fail(f"Publishing to an event with no subscribers raised an exception: {e}")

def test_multiple_subscribers():
    bus = EventBus()
    call_count = {"count": 0}

    def handler1():
        call_count["count"] += 1

    def handler2():
        call_count["count"] += 1

    bus.subscribe("multi_event", handler1)
    bus.subscribe("multi_event", handler2)
    bus.publish("multi_event")

    assert call_count["count"] == 2

def test_publish_with_arguments():
    bus = EventBus()
    result = {}

    def handler(name, value):
        result[name] = value

    bus.subscribe("args_event", handler)
    bus.publish("args_event", "foo", value="bar")

    assert result["foo"] == "bar"
