"""Тесты BaseComponent из SDK."""
import pytest
from unittest.mock import MagicMock
from typing import Dict, Any

from sdk.base_component import BaseComponent


class ConcreteComponent(BaseComponent):
    """Минимальная реализация для тестирования."""
    def __init__(self, bus):
        self._state = {"counter": 0}
        super().__init__(
            component_id="test_comp",
            component_type="test",
            topic="components.test",
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler("inc", self._handle_inc)

    def _handle_inc(self, message: Dict[str, Any]) -> Dict[str, Any]:
        self._state["counter"] += message.get("payload", {}).get("value", 1)
        return {"counter": self._state["counter"]}


@pytest.fixture
def bus():
    return MagicMock()


@pytest.fixture
def comp(bus):
    return ConcreteComponent(bus)


def test_handlers_registered(comp):
    assert "inc" in comp._handlers
    assert "ping" in comp._handlers
    assert "get_status" in comp._handlers


def test_handle_ping(comp):
    result = comp._handle_ping({})
    assert result["pong"] is True
    assert result["component_id"] == "test_comp"


def test_handle_get_status(comp):
    result = comp._handle_get_status({})
    assert result["component_id"] == "test_comp"
    assert result["component_type"] == "test"
    assert "inc" in result["handlers"]


def test_custom_handler(comp):
    msg = {"action": "inc", "sender": "x", "payload": {"value": 3}}
    result = comp._handle_inc(msg)
    assert result["counter"] == 3


def test_start(comp, bus):
    comp.start()
    bus.start.assert_called_once()
    bus.subscribe.assert_called_once()
    assert comp._running is True


def test_stop(comp, bus):
    comp._running = True
    comp.stop()
    bus.unsubscribe.assert_called_once()
    bus.stop.assert_called_once()
    assert comp._running is False


def test_message_routing_with_reply(comp, bus):
    msg = {
        "action": "inc",
        "sender": "client",
        "payload": {"value": 5},
        "reply_to": "replies.client",
        "correlation_id": "c1",
    }
    comp._handle_message(msg)
    bus.publish.assert_called_once()
    call_args = bus.publish.call_args[0]
    assert call_args[0] == "replies.client"
    assert call_args[1]["success"] is True
    assert call_args[1]["payload"]["counter"] == 5


def test_message_routing_unknown_action(comp, bus):
    msg = {"action": "nonexistent", "sender": "x"}
    comp._handle_message(msg)
    bus.publish.assert_not_called()


def test_log_security_no_op_when_env_unset(comp, bus, monkeypatch):
    monkeypatch.delenv("SECURITY_MONITOR_TOPIC", raising=False)
    comp._log_security("warning", "x.denied", "msg", details={"k": "v"})
    bus.publish.assert_not_called()


def test_log_security_publishes_when_topic_set(comp, bus, monkeypatch):
    monkeypatch.setenv("SECURITY_MONITOR_TOPIC", "systems.drone_port")
    comp._log_security(
        "warning",
        "request_landing.no_free_ports",
        "Landing denied",
        details={"drone_id": "DR-1"},
    )

    bus.publish.assert_called_once()
    topic, message = bus.publish.call_args[0]
    assert topic == "systems.drone_port"
    assert message["action"] == "log_event"
    assert message["sender"] == "components.test"
    payload = message["payload"]
    assert payload["severity"] == "warning"
    assert payload["source_component"] == "test"
    assert payload["source_action"] == "request_landing.no_free_ports"
    assert payload["message"] == "Landing denied"
    assert payload["details"] == {"drone_id": "DR-1"}


def test_log_security_swallows_bus_errors(comp, bus, monkeypatch):
    monkeypatch.setenv("SECURITY_MONITOR_TOPIC", "systems.drone_port")
    bus.publish.side_effect = RuntimeError("broker down")
    comp._log_security("error", "x.failed", "boom")  # must not raise


def test_log_security_defaults_details_to_empty_dict(comp, bus, monkeypatch):
    monkeypatch.setenv("SECURITY_MONITOR_TOPIC", "systems.gcs")
    comp._log_security("info", "x.ok", "ok")
    payload = bus.publish.call_args[0][1]["payload"]
    assert payload["details"] == {}
