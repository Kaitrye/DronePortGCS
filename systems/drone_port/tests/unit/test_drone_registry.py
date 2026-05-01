import pytest
from systems.drone_port.src.drone_registry.src.drone_registry import DroneRegistry
from systems.drone_port.src.drone_registry.topics import DroneRegistryActions


def test_registers_all_handlers(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)

    assert DroneRegistryActions.REGISTER_DRONE in registry._handlers
    assert DroneRegistryActions.REMOVE_DRONE in registry._handlers
    assert DroneRegistryActions.GET_AVAILABLE_DRONES in registry._handlers
    assert DroneRegistryActions.UPDATE_BATTERY in registry._handlers
    assert DroneRegistryActions.GET_DRONE in registry._handlers


def test_register_drone_stores_metadata(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)

    registry._handle_register(
        {"payload": {"drone_id": "DR-1", "port_id": "P-01", "battery": 75.0}}
    )

    saved = registry.redis.hgetall("drone:DR-1")
    assert saved["drone_id"] == "DR-1"
    assert saved["port_id"] == "P-01"
    assert saved["battery"] == 75.0
    assert saved["status"] == "registered"
    assert "registered_at" in saved


def test_register_drone_ignores_invalid_payload(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)

    registry._handle_register({"payload": None})
    registry._handle_register({"payload": {}})
    registry._handle_register({"payload": {"drone_id": ""}})

    # Нет новых ключей
    keys = [k for k in registry.redis.data if k.startswith("drone:") and k != "drone:drone_001"]
    assert len(keys) == 0


def test_remove_drone_deletes_key(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)
    registry.redis.hset("drone:DR-9", {"drone_id": "DR-9"})

    registry._handle_remove({"payload": {"drone_id": "DR-9"}})

    assert "drone:DR-9" not in registry.redis.data


def test_get_available_drones_returns_only_drones_with_battery_60_plus(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)
    registry.redis.hset("drone:DR-1", {"drone_id": "DR-1", "battery": 90.0})
    registry.redis.hset("drone:DR-2", {"drone_id": "DR-2", "battery": 45.0})

    result = registry._handle_get_available({"payload": {}})

    drone_ids = [d["drone_id"] for d in result["drones"]]
    assert "DR-1" in drone_ids
    assert "DR-2" not in drone_ids


def test_get_drone_returns_drone_data(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)
    registry.redis.hset("drone:DR-5", {"drone_id": "DR-5", "battery": 80.0, "port_id": "P-01"})

    result = registry._handle_get_drone({"payload": {"drone_id": "DR-5"}})

    assert result["drone_id"] == "DR-5"
    assert result["battery"] == 80.0
    assert result["port_id"] == "P-01"


def test_get_drone_returns_error_when_not_found(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)

    result = registry._handle_get_drone({"payload": {"drone_id": "missing"}})

    assert result == {"error": "Drone not found"}


def test_update_battery_marks_drone_ready_at_full_charge(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)
    registry.redis.hset("drone:DR-3", {"drone_id": "DR-3", "status": "charging"})

    registry._handle_update_battery({"payload": {"drone_id": "DR-3", "battery": 100.0}})

    saved = registry.redis.hgetall("drone:DR-3")
    assert saved["battery"] == 100.0
    assert saved["status"] == "ready"


def test_update_battery_partial_stays_charging(mock_bus, patch_droneport_redis):
    registry = DroneRegistry(component_id="registry", name="Registry", bus=mock_bus)
    registry.redis.hset("drone:DR-4", {"drone_id": "DR-4"})

    registry._handle_update_battery({"payload": {"drone_id": "DR-4", "battery": 42.0}})

    saved = registry.redis.hgetall("drone:DR-4")
    assert saved["battery"] == 42.0
    assert saved["status"] == "charging"