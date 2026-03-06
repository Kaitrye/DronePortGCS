"""
Тесты компонента DroneRegistry (учёт дронов и их состояния).
Включают тесты для новых методов регистрации и получения дронов.
"""
import pytest
from unittest.mock import Mock
from src.state_store.src.state_store import StateStore
from src.drone_registry.src.drone_registry import DroneRegistry


@pytest.fixture
def mock_state_store():
    """Мок StateStore для изоляции."""
    mock = Mock()
    mock.save_drone.return_value = True
    mock.register_drone_meta.return_value = True
    mock.get_drone.return_value = None
    mock.list_drones.return_value = []
    return mock


@pytest.fixture
def registry(mock_state_store):
    """DroneRegistry с моком StateStore."""
    return DroneRegistry(mock_state_store)


def test_register_drone(registry, mock_state_store):
    """Тест регистрации дрона в реестре."""
    specs = {
        "drone_type": "agricultural",
        "max_speed_kmh": "60",
        "protocol": "MAVLink"
    }
    
    result = registry.register_drone(
        drone_id="D-001",
        battery_level=50.0,
        port_id="P-01",
        specs=specs
    )
    
    assert result["status"] == "registered"
    assert result["drone_id"] == "D-001"
    mock_state_store.save_drone.assert_called_once()
    mock_state_store.register_drone_meta.assert_called_once_with("D-001", specs)


def test_register_drone_without_specs(registry, mock_state_store):
    """Тест регистрации дрона без спецификаций."""
    result = registry.register_drone(
        drone_id="D-002",
        battery_level=75.0,
        port_id="P-02"
    )
    
    assert result["status"] == "registered"
    # register_drone_meta не должен вызываться без specs
    mock_state_store.register_drone_meta.assert_not_called()


def test_get_drone_normal_operation(registry, mock_state_store):
    """Тест получения дрона с нормальным статусом."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "85.0",
        "status": "landed",
        "port_id": "P-01"
    }
    
    drone = registry.get_drone("D-001")
    
    assert drone["drone_id"] == "D-001"
    assert drone["battery_level"] == 85.0
    assert drone["safety_target"] == "normal_operation"
    assert drone["issues"] == []


def test_get_drone_low_battery_alert(registry, mock_state_store):
    """Тест получения дрона с низким зарядом батареи."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "15.0",
        "status": "landed",
        "port_id": "P-01"
    }
    
    drone = registry.get_drone("D-001")
    
    assert drone["safety_target"] == "low_battery_alert"
    assert "battery_critical" in drone["issues"]


def test_get_drone_not_found(registry, mock_state_store):
    """Тест получения несуществующего дрона."""
    mock_state_store.get_drone.return_value = None
    
    drone = registry.get_drone("D-999")
    
    assert drone is None


def test_run_post_landing_diagnostics_success(registry, mock_state_store):
    """Тест успешной пост-посадочной диагностики."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "75.0",
        "status": "landed"
    }
    
    result = registry.run_post_landing_diagnostics("D-001")
    
    assert result["status"] == "diagnostics.ok"
    assert result["drone_id"] == "D-001"


def test_run_post_landing_diagnostics_failed(registry, mock_state_store):
    """Тест неудачной пост-посадочной диагностики (низкий заряд)."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "8.0",
        "status": "landed"
    }
    
    result = registry.run_post_landing_diagnostics("D-001")
    
    assert result["status"] == "diagnostics.failed"
    assert "battery_critical" in result["issues"]


def test_run_post_landing_diagnostics_drone_not_found(registry, mock_state_store):
    """Тест диагностики для несуществующего дрона."""
    mock_state_store.get_drone.return_value = None
    
    result = registry.run_post_landing_diagnostics("D-999")
    
    assert result["status"] == "diagnostics.failed"
    assert result["error_code"] == "DRONE_NOT_FOUND"


def test_list_all_drones_empty(registry, mock_state_store):
    """Тест пустого списка дронов."""
    mock_state_store.list_drones.return_value = []
    
    drones = registry.list_all_drones()
    
    assert drones == []


def test_list_all_drones_with_data(registry, mock_state_store):
    """Тест списка дронов с данными."""
    mock_state_store.list_drones.return_value = [
        {"drone_id": "D-001", "battery_level": "45.0", "status": "landed", "port_id": "P-01"},
        {"drone_id": "D-002", "battery_level": "10.0", "status": "charging", "port_id": "P-02"}
    ]
    
    drones = registry.list_all_drones()
    
    assert len(drones) == 2
    assert drones[0]["safety_target"] == "normal_operation"
    assert drones[1]["safety_target"] == "low_battery_alert"
    assert "battery_critical" in drones[1]["issues"]