import pytest

from systems.drone_port.src.landing_manager.src.landing_manager import LandingManager
from systems.drone_port.src.landing_manager.topics import ComponentTopics, LandingManagerActions
from systems.drone_port.src.drone_registry.topics import DroneRegistryActions
from systems.drone_port.src.port_manager.topics import PortManagerActions
from systems.drone_port.src.charging_manager.topics import ChargingManagerActions


@pytest.fixture
def component(mock_bus):
    return LandingManager(component_id="landing_manager", name="LandingManager", bus=mock_bus)


def test_registers_landing_handler(component):
    assert LandingManagerActions.REQUEST_LANDING in component._handlers


def test_landing_occupies_port_registers_drone_starts_charging(mock_bus):
    manager = LandingManager(component_id="landing_manager", name="LandingManager", bus=mock_bus)
    mock_bus.request.return_value = {"port_id": "P-01"}

    result = manager._handle_landing({"payload": {"drone_id": "DR-1", "battery": 45.0}})

    assert result == {"approved": True, "port_id": "P-01", "drone_id": "DR-1"}

    # Проверяем occupy_port
    mock_bus.request.assert_called_once_with(
        ComponentTopics.PORT_MANAGER,
        {
            "action": LandingManagerActions.OCCUPY_PORT,
            "payload": {"drone_id": "DR-1"},
            "sender": "landing_manager",
        },
        timeout=5.0,
    )

    # Проверяем register_drone
    assert mock_bus.publish.call_args_list[0].args == (
        ComponentTopics.DRONE_REGISTRY,
        {
            "action": LandingManagerActions.REGISTER_DRONE,
            "payload": {"drone_id": "DR-1", "port_id": "P-01", "battery": 45.0},
            "sender": "landing_manager",
        },
    )

    # Проверяем start_charging
    assert mock_bus.publish.call_args_list[1].args == (
        ComponentTopics.CHARGING_MANAGER,
        {
            "action": LandingManagerActions.START_CHARGING,
            "payload": {"drone_id": "DR-1", "battery": 45.0},
            "sender": "landing_manager",
        },
    )


def test_landing_with_full_battery_does_not_start_charging(mock_bus):
    manager = LandingManager(component_id="landing_manager", name="LandingManager", bus=mock_bus)
    mock_bus.request.return_value = {"port_id": "P-01"}

    result = manager._handle_landing({"payload": {"drone_id": "DR-2", "battery": 100.0}})

    assert result == {"approved": True, "port_id": "P-01", "drone_id": "DR-2"}

    # register_drone есть, start_charging нет
    assert mock_bus.publish.call_count == 1
    assert mock_bus.publish.call_args.args[1]["action"] == LandingManagerActions.REGISTER_DRONE


def test_landing_returns_error_when_no_free_ports(mock_bus):
    manager = LandingManager(component_id="landing_manager", name="LandingManager", bus=mock_bus)
    mock_bus.request.return_value = {"error": "No free ports"}

    result = manager._handle_landing({"payload": {"drone_id": "DR-3", "battery": 50.0}})

    assert result == {"error": "No free ports"}
    assert mock_bus.publish.call_count == 0


def test_landing_returns_error_without_drone_id(mock_bus):
    manager = LandingManager(component_id="landing_manager", name="LandingManager", bus=mock_bus)

    result = manager._handle_landing({"payload": {"battery": 50.0}})

    assert result == {"error": "drone_id required"}
    mock_bus.request.assert_not_called()
    mock_bus.publish.assert_not_called()