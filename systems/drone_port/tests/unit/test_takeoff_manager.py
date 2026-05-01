import pytest

from systems.drone_port.src.takeoff_manager.src.takeoff_manager import TakeoffManager
from systems.drone_port.src.takeoff_manager.topics import ComponentTopics, TakeoffManagerActions
from systems.drone_port.src.drone_registry.topics import DroneRegistryActions
from systems.drone_port.src.port_manager.topics import PortManagerActions


@pytest.fixture
def component(mock_bus):
    return TakeoffManager(component_id="takeoff_manager", name="TakeoffManager", bus=mock_bus)


def test_registers_takeoff_handler(component):
    assert TakeoffManagerActions.REQUEST_TAKEOFF in component._handlers


def test_takeoff_releases_port_removes_drone_when_battery_sufficient(mock_bus):
    manager = TakeoffManager(component_id="takeoff_manager", name="TakeoffManager", bus=mock_bus)

    def request_side_effect(topic, message, timeout=None):
        if message["action"] == TakeoffManagerActions.GET_DRONE:
            return {"drone_id": "DR-1", "port_id": "P-01", "battery": 85.0}
        return {}

    mock_bus.request.side_effect = request_side_effect

    result = manager._handle_takeoff({"payload": {"drone_id": "DR-1"}})

    assert result == {"approved": True, "drone_id": "DR-1", "battery": 85.0}

    # Проверяем release_port
    assert mock_bus.publish.call_args_list[0].args == (
        ComponentTopics.PORT_MANAGER,
        {
            "action": TakeoffManagerActions.RELEASE_PORT,
            "payload": {"port_id": "P-01", "drone_id": "DR-1"},
            "sender": "takeoff_manager",
        },
    )

    # Проверяем remove_drone
    assert mock_bus.publish.call_args_list[1].args == (
        ComponentTopics.DRONE_REGISTRY,
        {
            "action": TakeoffManagerActions.REMOVE_DRONE,
            "payload": {"drone_id": "DR-1"},
            "sender": "takeoff_manager",
        },
    )


def test_takeoff_returns_error_when_battery_too_low(mock_bus):
    manager = TakeoffManager(component_id="takeoff_manager", name="TakeoffManager", bus=mock_bus)

    def request_side_effect(topic, message, timeout=None):
        if message["action"] == TakeoffManagerActions.GET_DRONE:
            return {"drone_id": "DR-1", "port_id": "P-01", "battery": 45.0}
        return {}

    mock_bus.request.side_effect = request_side_effect

    result = manager._handle_takeoff({"payload": {"drone_id": "DR-1"}})

    assert result == {"error": "Not enough battery for takeoff", "battery": 45.0}
    assert mock_bus.publish.call_count == 0


def test_takeoff_returns_error_when_drone_not_found(mock_bus):
    manager = TakeoffManager(component_id="takeoff_manager", name="TakeoffManager", bus=mock_bus)

    def request_side_effect(topic, message, timeout=None):
        if message["action"] == TakeoffManagerActions.GET_DRONE:
            return {"error": "Drone not found"}
        return {}

    mock_bus.request.side_effect = request_side_effect

    result = manager._handle_takeoff({"payload": {"drone_id": "DR-404"}})

    assert result == {"error": "Drone not found"}
    assert mock_bus.publish.call_count == 0


def test_takeoff_returns_error_without_drone_id(mock_bus):
    manager = TakeoffManager(component_id="takeoff_manager", name="TakeoffManager", bus=mock_bus)

    result = manager._handle_takeoff({"payload": {}})

    assert result == {"error": "drone_id required"}
    mock_bus.request.assert_not_called()
    mock_bus.publish.assert_not_called()