import pytest

from systems.drone_port.src.charging_manager.src import charging_manager as charging_manager_module
from systems.drone_port.src.charging_manager.src.charging_manager import ChargingManager
from systems.drone_port.src.charging_manager.topics import ComponentTopics, ChargingManagerActions
from systems.drone_port.src.drone_registry.topics import DroneRegistryActions


def test_registers_start_charging_handler(mock_bus):
    manager = ChargingManager(component_id="charging_manager", name="Charging", bus=mock_bus)
    assert ChargingManagerActions.START_CHARGING in manager._handlers


def test_start_charging_spawns_worker(mock_bus, monkeypatch):
    captured = {}

    class FakeThread:
        def __init__(self, target, args=(), daemon=None):
            captured["target"] = target
            captured["args"] = args
            captured["daemon"] = daemon

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(charging_manager_module.threading, "Thread", FakeThread)
    manager = ChargingManager(component_id="charging_manager", name="Charging", bus=mock_bus)

    result = manager._handle_start_charging(
        {"payload": {"drone_id": "DR-1", "battery": 45.0}}
    )

    assert result == {"started": True, "drone_id": "DR-1"}
    assert captured["args"] == ("DR-1", 45.0)
    assert captured["started"] is True


def test_start_charging_uses_default_battery_when_missing(mock_bus, monkeypatch):
    captured = {}

    class FakeThread:
        def __init__(self, target, args=(), daemon=None):
            captured["args"] = args

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(charging_manager_module.threading, "Thread", FakeThread)
    manager = ChargingManager(component_id="charging_manager", name="Charging", bus=mock_bus)

    result = manager._handle_start_charging({"payload": {"drone_id": "DR-9"}})

    assert result == {"started": True, "drone_id": "DR-9"}
    assert captured["args"] == ("DR-9", 0.0)


def test_start_charging_returns_error_without_drone_id(mock_bus):
    manager = ChargingManager(component_id="charging_manager", name="Charging", bus=mock_bus)

    result = manager._handle_start_charging({"payload": {"battery": 45.0}})
    assert result == {"error": "drone_id required"}


@pytest.mark.parametrize(
    "battery, expected",
    [
        (95.0, [96.0, 97.0, 98.0, 99.0, 100.0]),
        (100.0, []),
        (150.0, []),
    ],
)
def test_simulate_charging_boundary_battery_values(mock_bus, monkeypatch, battery, expected):
    manager = ChargingManager(component_id="charging_manager", name="Charging", bus=mock_bus)
    monkeypatch.setattr(charging_manager_module.time, "sleep", lambda *_args, **_kwargs: None)

    manager._simulate_charging("DR-X", battery)

    published_battery = [
        call.args[1]["payload"]["battery"] for call in mock_bus.publish.call_args_list
    ]
    assert published_battery == expected


def test_simulate_charging_clamps_negative_battery_and_reaches_full(mock_bus, monkeypatch):
    manager = ChargingManager(component_id="charging_manager", name="Charging", bus=mock_bus)
    monkeypatch.setattr(charging_manager_module.time, "sleep", lambda *_args, **_kwargs: None)

    manager._simulate_charging("DR-NEG", -5.0)

    published_battery = [
        call.args[1]["payload"]["battery"] for call in mock_bus.publish.call_args_list
    ]
    assert published_battery[0] == 1.0
    assert published_battery[-1] == 100.0


def test_simulate_charging_publishes_updates_until_full(mock_bus, monkeypatch):
    manager = ChargingManager(component_id="charging_manager", name="Charging", bus=mock_bus)
    monkeypatch.setattr(charging_manager_module.time, "sleep", lambda *_args, **_kwargs: None)

    manager._simulate_charging("DR-2", 85.0)

    published = [call.args for call in mock_bus.publish.call_args_list]
    assert published[0] == (
        ComponentTopics.DRONE_REGISTRY,
        {
            "action": DroneRegistryActions.UPDATE_BATTERY,
            "payload": {"drone_id": "DR-2", "battery": 86.0},
            "sender": "charging_manager",
        },
    )
    assert published[-1] == (
        ComponentTopics.DRONE_REGISTRY,
        {
            "action": DroneRegistryActions.UPDATE_BATTERY,
            "payload": {"drone_id": "DR-2", "battery": 100.0},
            "sender": "charging_manager",
        },
    )