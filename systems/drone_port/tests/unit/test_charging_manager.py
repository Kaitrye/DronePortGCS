"""
Тесты для ChargingManager.
"""
import pytest
from unittest.mock import Mock
from src.charging_manager.src.charging_manager import ChargingManager

@pytest.fixture
def mock_bus():
    mock = Mock()
    mock.subscribe = Mock()
    mock.publish = Mock()
    mock.request = Mock()
    return mock

@pytest.fixture
def mock_state_store():
    mock = Mock()
    mock.get_drone.return_value = None
    mock.save_drone.return_value = True
    mock.list_drones.return_value = []
    return mock

@pytest.fixture
def charging_manager(mock_bus, mock_state_store):
    manager = ChargingManager(
        system_id="dp-001",
        name="TestCharging",
        bus=mock_bus,
        state_store=mock_state_store
    )
    return manager

class TestChargingOperations:
    """Тесты операций зарядки."""
    
    def test_start_charging_success(self, charging_manager, mock_state_store):
        """Успешное начало зарядки."""
        mock_state_store.get_drone.return_value = {
            "drone_id": "D-001",
            "battery_level": "45.0",
            "status": "landed"
        }
        
        message = {"payload": {"drone_id": "D-001"}}
        result = charging_manager._handle_start_charging(message)
        
        assert result["status"] == "charging_started"
        mock_state_store.save_drone.assert_called_once()
    
    def test_start_charging_drone_not_found(self, charging_manager, mock_state_store):
        """Начало зарядки для несуществующего дрона."""
        mock_state_store.get_drone.return_value = None
        
        message = {"payload": {"drone_id": "D-999"}}
        result = charging_manager._handle_start_charging(message)
        
        assert result["status"] == "failed"
        assert result["reason"] == "Drone not found"
    
    def test_stop_charging(self, charging_manager, mock_state_store):
        """Остановка зарядки."""
        mock_state_store.get_drone.return_value = {
            "drone_id": "D-001",
            "status": "charging"
        }
        
        message = {"payload": {"drone_id": "D-001"}}
        result = charging_manager._handle_stop_charging(message)
        
        assert result["status"] == "charging_stopped"
    
    def test_charge_to_threshold_not_required(self, charging_manager, mock_state_store):
        """Зарядка не требуется (батарея уже заряжена)."""
        message = {
            "payload": {
                "drone_id": "D-001",
                "min_battery": 80.0,
                "current_battery": 85.0
            }
        }
        
        result = charging_manager._handle_charge_to_threshold(message)
        
        assert result["status"] == "charge.not_required"
        assert result["battery_level"] == 85.0
    
    def test_charge_to_threshold_success(self, charging_manager, mock_state_store):
        """Успешный расчёт зарядки до порога."""
        mock_state_store.get_drone.return_value = {
            "drone_id": "D-001",
            "battery_level": "50.0"
        }
        
        message = {
            "payload": {
                "drone_id": "D-001",
                "min_battery": 90.0,
                "current_battery": 50.0,
                "departure_time_sec": 3600
            }
        }
        
        result = charging_manager._handle_charge_to_threshold(message)
        
        assert result["status"] == "charge.completed"
        assert result["charging_power_w"] > 0
        assert "estimated_finish_sec" in result
    
    def test_get_charging_status(self, charging_manager, mock_state_store):
        """Получение статуса зарядки."""
        mock_state_store.list_drones.return_value = [
            {"drone_id": "D-001", "status": "charging", "battery_level": "45.0", "charging_power_w": "500"},
            {"drone_id": "D-002", "status": "landed", "battery_level": "90.0"}
        ]
        
        message = {"payload": {}}
        result = charging_manager._handle_get_charging_status(message)
        
        assert result["status"] == "ok"
        assert len(result["payload"]) == 1
        assert result["payload"][0]["drone_id"] == "D-001"
        assert result["payload"][0]["battery_level"] == "45.0"