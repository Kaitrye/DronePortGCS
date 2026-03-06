"""
Тесты компонента PortManager (резервирование и освобождение площадок).
Включают тесты для новой валидации совместимости дронов.
"""
import pytest
from unittest.mock import Mock
from src.state_store.src.state_store import StateStore
from src.port_manager.src.port_manager import PortManager


@pytest.fixture
def mock_state_store():
    """Мок StateStore для изоляции."""
    mock = Mock()
    mock.is_port_occupied.return_value = False
    mock.save_port.return_value = True
    mock.save_drone.return_value = True
    mock.get_port.return_value = None
    mock.get_drone_meta.return_value = None
    return mock


@pytest.fixture
def port_manager(mock_state_store):
    """PortManager с моком StateStore."""
    return PortManager(mock_state_store)


def test_validate_drone_compatibility_success(port_manager, mock_state_store):
    """Тест успешной валидации совместимости дрона."""
    mock_state_store.get_drone_meta.return_value = {
        "drone_type": "agricultural",
        "protocol": "MAVLink"
    }
    mock_state_store.get_port.return_value = {
        "port_id": "P-01",
        "max_load_kg": "100",
        "supported_protocol": "MAVLink",
        "maintenance_mode": "false"
    }
    
    is_valid, err_code, reason = port_manager._validate_drone_compatibility("D-001", "P-01")
    
    assert is_valid is True
    assert err_code is None
    assert reason is None


def test_validate_drone_type_mismatch(port_manager, mock_state_store):
    """Тест отказа из-за несоответствия типа дрона."""
    mock_state_store.get_drone_meta.return_value = {
        "drone_type": "heavy_cargo",
        "protocol": "MAVLink"
    }
    mock_state_store.get_port.return_value = {
        "port_id": "P-01",
        "max_load_kg": "20",  # Порт не выдержит тяжёлый дрон
        "supported_protocol": "MAVLink",
        "maintenance_mode": "false"
    }
    
    is_valid, err_code, reason = port_manager._validate_drone_compatibility("D-001", "P-01")
    
    assert is_valid is False
    assert err_code == "DRONE_TYPE_MISMATCH"
    assert "heavy cargo" in reason


def test_validate_protocol_mismatch(port_manager, mock_state_store):
    """Тест отказа из-за несоответствия протокола связи."""
    mock_state_store.get_drone_meta.return_value = {
        "drone_type": "agricultural",
        "protocol": "CustomProto"
    }
    mock_state_store.get_port.return_value = {
        "port_id": "P-01",
        "max_load_kg": "100",
        "supported_protocol": "MAVLink",
        "maintenance_mode": "false"
    }
    
    is_valid, err_code, reason = port_manager._validate_drone_compatibility("D-001", "P-01")
    
    assert is_valid is False
    assert err_code == "PROTOCOL_MISMATCH"


def test_validate_port_maintenance(port_manager, mock_state_store):
    """Тест отказа из-за обслуживания порта."""
    mock_state_store.get_port.return_value = {
        "port_id": "P-01",
        "maintenance_mode": "true"
    }
    
    is_valid, err_code, reason = port_manager._validate_drone_compatibility("D-001", "P-01")
    
    assert is_valid is False
    assert err_code == "PORT_MAINTENANCE"


def test_request_landing_slot_with_validation_success(port_manager, mock_state_store):
    """Тест успешного запроса посадочного слота с валидацией."""
    mock_state_store.is_port_occupied.return_value = False
    mock_state_store.get_drone_meta.return_value = {
        "drone_type": "agricultural",
        "protocol": "MAVLink"
    }
    mock_state_store.get_port.return_value = {
        "port_id": "P-01",
        "max_load_kg": "100",
        "supported_protocol": "MAVLink",
        "maintenance_mode": "false"
    }
    
    result = port_manager.request_landing_slot(
        drone_id="D-001",
        preferred_ports=["P-01", "P-02"]
    )
    
    assert result["status"] == "slot_assigned"
    assert result["port_id"] == "P-01"
    assert "corridor" in result


def test_request_landing_slot_all_ports_unsuitable(port_manager, mock_state_store):
    """Тест отказа, когда все порты не подходят по безопасности."""
    mock_state_store.is_port_occupied.return_value = False
    mock_state_store.get_port.return_value = {
        "port_id": "P-01",
        "maintenance_mode": "true"  # Все порты на обслуживании
    }
    
    result = port_manager.request_landing_slot(
        drone_id="D-001",
        preferred_ports=["P-01", "P-02"]
    )
    
    assert result["status"] == "denied"
    assert result["error_code"] == "NO_SUITABLE_SLOTS"
    assert result["retryable"] is True


def test_generate_landing_corridor(port_manager):
    """Тест генерации коридора посадки."""
    corridor = port_manager._generate_landing_corridor("P-01")
    
    assert "entry_point" in corridor
    assert "altitude_m" in corridor
    assert "approach_vector" in corridor
    assert corridor["altitude_m"] == 50


def test_reserve_slot_success(port_manager, mock_state_store):
    """Тест успешного резервирования слота."""
    result = port_manager.reserve_slot(
        drone_id="D-001",
        port_id="P-01",
        mission_window={"start": "2026-02-27T12:00:00Z", "end": "2026-02-27T13:00:00Z"}
    )
    
    assert result["status"] == "reserved"
    assert result["port_id"] == "P-01"


def test_reserve_slot_already_occupied(port_manager, mock_state_store):
    """Тест отказа при занятом порте."""
    mock_state_store.is_port_occupied.return_value = True
    
    result = port_manager.reserve_slot("D-001", "P-01", {})
    
    assert result["status"] == "rejected"
    assert result["error_code"] == "PORT_RESOURCE_BUSY"


def test_release_for_takeoff_success(port_manager, mock_state_store):
    """Тест успешного освобождения для взлёта."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "port_id": "P-01"
    }
    
    result = port_manager.release_for_takeoff("D-001")
    
    assert result["status"] == "release_ack"
    mock_state_store.save_port.assert_called_once()
    mock_state_store.delete_drone.assert_called_once()


def test_release_for_takeoff_drone_not_found(port_manager, mock_state_store):
    """Тест освобождения для несуществующего дрона."""
    mock_state_store.get_drone.return_value = None
    
    result = port_manager.release_for_takeoff("D-999")
    
    assert result["status"] == "failed"
    assert "not found" in result["reason"]