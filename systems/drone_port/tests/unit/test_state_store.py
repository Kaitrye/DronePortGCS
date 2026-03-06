"""
Тесты компонента StateStore (хранение состояния в Redis).
Включают тесты для новых методов агрегации и мета-данных.
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.state_store.src.state_store import StateStore


@pytest.fixture
def mock_redis():
    """Мок Redis клиента."""
    mock = Mock()
    mock.keys.return_value = []
    mock.hgetall.return_value = {}
    mock.hset.return_value = 1
    mock.delete.return_value = 1
    return mock


@pytest.fixture
def state_store(mock_redis):
    """StateStore с моком Redis."""
    store = StateStore()
    store.redis = mock_redis
    return store


def test_save_and_get_drone(state_store, mock_redis):
    drone_data = {
        "drone_id": "D-001",
        "battery_level": "45.0",
        "status": "landed"
    }
    mock_redis.hgetall.return_value = drone_data
    
    state_store.save_drone("D-001", drone_data)
    retrieved = state_store.get_drone("D-001")
    
    assert retrieved == drone_data
    mock_redis.hset.assert_called_once_with("drone:D-001", mapping=drone_data)


def test_list_drones_empty(state_store):
    drones = state_store.list_drones()
    assert drones == []


def test_list_drones_with_data(state_store, mock_redis):
    mock_redis.keys.return_value = ["drone:D-001", "drone:D-002"]
    mock_redis.hgetall.side_effect = [
        {"drone_id": "D-001", "battery_level": "30.0"},
        {"drone_id": "D-002", "battery_level": "80.0"}
    ]
    
    drones = state_store.list_drones()
    
    assert len(drones) == 2
    assert drones[0]["drone_id"] == "D-001"


def test_register_drone_meta(state_store, mock_redis):
    """Тест сохранения спецификаций дрона."""
    specs = {
        "drone_type": "heavy_cargo",
        "max_load_kg": "50",
        "protocol": "MAVLink"
    }
    
    result = state_store.register_drone_meta("D-001", specs)
    
    assert result is True
    mock_redis.hset.assert_called_once_with("drone_meta:D-001", mapping=specs)


def test_get_drone_meta_exists(state_store, mock_redis):
    """Тест получения спецификаций дрона."""
    specs = {
        "drone_type": "heavy_cargo",
        "max_load_kg": "50",
        "protocol": "MAVLink"
    }
    mock_redis.hgetall.return_value = specs
    
    result = state_store.get_drone_meta("D-001")
    
    assert result == specs
    mock_redis.hgetall.assert_called_once_with("drone_meta:D-001")


def test_get_drone_meta_not_exists(state_store, mock_redis):
    """Тест получения несуществующих спецификаций."""
    mock_redis.hgetall.return_value = {}
    
    result = state_store.get_drone_meta("D-999")
    
    assert result is None


def test_get_all_ports_status(state_store, mock_redis):
    """Тест получения статуса всех портов."""
    mock_redis.keys.return_value = ["port:P-01", "port:P-02"]
    mock_redis.hgetall.side_effect = [
        {"port_id": "P-01", "drone_id": "D-001", "status": "occupied"},
        {"port_id": "P-02", "drone_id": "", "status": "free"}
    ]
    
    ports = state_store.get_all_ports_status()
    
    assert len(ports) == 2
    assert ports[0]["port_id"] == "P-01"
    assert ports[1]["status"] == "free"


def test_get_aggregated_fleet_status(state_store, mock_redis):
    """Тест агрегации данных для отчёта эксплуатанту."""
    # Мок для list_drones
    mock_redis.keys.side_effect = [
        ["drone:D-001", "drone:D-002", "drone:D-003"],  # drones
        ["port:P-01", "port:P-02", "port:P-03", "port:P-04"]  # ports
    ]
    mock_redis.hgetall.side_effect = [
        # Drones
        {"drone_id": "D-001", "status": "charging", "battery_level": "45.0"},
        {"drone_id": "D-002", "status": "landed", "battery_level": "90.0"},
        {"drone_id": "D-003", "status": "landed", "battery_level": "15.0", "issues": "battery_critical"},
        # Ports
        {"port_id": "P-01", "drone_id": "D-001", "status": "occupied"},
        {"port_id": "P-02", "drone_id": "D-002", "status": "occupied"},
        {"port_id": "P-03", "drone_id": "", "status": "free"},
        {"port_id": "P-04", "drone_id": "", "status": "maintenance"}
    ]
    
    report = state_store.get_aggregated_fleet_status()
    
    assert "timestamp" in report
    assert report["fleet"]["total"] == 3
    assert report["fleet"]["charging"] == 1
    assert report["fleet"]["ready"] == 2
    assert report["fleet"]["issues"] == 1
    assert report["ports"]["total"] == 4
    assert report["ports"]["occupied"] == 2
    assert report["ports"]["maintenance"] == 1
    assert len(report["alerts"]) == 1
    assert report["alerts"][0]["drone_id"] == "D-003"