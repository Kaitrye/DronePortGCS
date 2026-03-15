"""
Тесты для DroneManager.
Включают тесты SITL интеграции и доступных дронов.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.drone_manager.src.drone_manager import DroneManager
from src.drone_manager.topics import DroneManagerTopics

@pytest.fixture
def mock_bus():
    """Мок SystemBus."""
    mock = Mock()
    mock.subscribe = Mock()
    mock.publish = Mock()
    mock.request = Mock()
    return mock

@pytest.fixture
def drone_manager(mock_bus):
    """DroneManager с моком шины."""
    manager = DroneManager(
        system_id="dp-001",
        name="TestDroneManager",
        bus=mock_bus
    )
    return manager

class TestSITLIntegration:
    """Тесты интеграции с SITL."""
    
    def test_get_sitl_data_single_drone(self, drone_manager, mock_bus):
        """Получение данных SITL для одного дрона."""
        drone_manager._drone_positions = {
            "D-001": {
                "lat": 55.7558,
                "lon": 37.6173,
                "alt": 100.0,
                "heading": 45.0,
                "vx": 5.0,
                "vy": 2.0,
                "vz": 0.0,
                "battery": 75.0,
                "mode": "AUTO",
                "armed": True
            }
        }
        
        message = {"payload": {"drone_id": "D-001"}}
        result = drone_manager._handle_get_sitl_data(message)
        
        assert result["status"] == "ok"
        assert result["drone_id"] == "D-001"
        assert result["position"]["lat"] == 55.7558
        assert result["position"]["alt"] == 100.0
        assert result["battery"] == 75.0
        assert result["mode"] == "AUTO"
        assert result["armed"] is True
    
    def test_get_sitl_data_all_drones(self, drone_manager, mock_bus):
        """Получение данных SITL для всех дронов."""
        drone_manager._drone_positions = {
            "D-001": {"lat": 55.7558, "lon": 37.6173, "alt": 100.0, "battery": 75.0, "mode": "AUTO", "armed": True},
            "D-002": {"lat": 55.7560, "lon": 37.6175, "alt": 150.0, "battery": 60.0, "mode": "STANDBY", "armed": False}
        }
        
        message = {"payload": {}}
        result = drone_manager._handle_get_sitl_data(message)
        
        assert result["status"] == "ok"
        assert result["total"] == 2
        assert len(result["drones"]) == 2
        assert result["drones"][0]["drone_id"] == "D-001"
        assert result["drones"][1]["drone_id"] == "D-002"
    
    def test_get_sitl_data_drone_not_found(self, drone_manager, mock_bus):
        """Запрос SITL данных для несуществующего дрона."""
        drone_manager._drone_positions = {}
        
        message = {"payload": {"drone_id": "D-999"}}
        result = drone_manager._handle_get_sitl_data(message)
        
        assert result["status"] == "ok"
        assert result["position"]["lat"] == 0.0
        assert result["battery"] == 100.0
    
    def test_update_sitl_position(self, drone_manager, mock_bus):
        """Обновление позиции дрона для SITL."""
        message = {
            "payload": {
                "drone_id": "D-001",
                "lat": 55.7558,
                "lon": 37.6173,
                "alt": 100.0,
                "heading": 45.0,
                "vx": 5.0,
                "vy": 2.0,
                "vz": 0.0,
                "battery": 75.0,
                "mode": "AUTO",
                "armed": True
            }
        }
        
        result = drone_manager._handle_update_sitl_position(message)
        
        assert result["status"] == "position_updated"
        assert "D-001" in drone_manager._drone_positions
        assert drone_manager._drone_positions["D-001"]["lat"] == 55.7558
        assert drone_manager._drone_positions["D-001"]["battery"] == 75.0
    
    def test_update_sitl_position_invalid_payload(self, drone_manager, mock_bus):
        """Обновление позиции с некорректным payload."""
        message = {"payload": {}}
        result = drone_manager._handle_update_sitl_position(message)
        
        assert result["status"] == "failed"
        assert result["error_code"] == "INVALID_PAYLOAD"

class TestAvailableDrones:
    """Тесты получения доступных дронов."""
    
    def test_get_available_drones_success(self, drone_manager, mock_bus):
        """Получение списка доступных дронов."""
        mock_bus.request.return_value = {
            "status": "ok",
            "drones": [
                {"drone_id": "D-001", "status": "landed", "battery_level": "85.0", "port_id": "P-01"},
                {"drone_id": "D-002", "status": "charging", "battery_level": "45.0", "port_id": "P-02"},
                {"drone_id": "D-003", "status": "maintenance", "battery_level": "0.0", "port_id": ""}
            ]
        }
        
        drone_manager._drone_positions = {
            "D-001": {"lat": 55.7558, "lon": 37.6173, "alt": 0.0},
            "D-002": {"lat": 55.7560, "lon": 37.6175, "alt": 0.0}
        }
        
        message = {"payload": {}}
        result = drone_manager._handle_get_available_drones(message)
        
        assert result["status"] == "ok"
        assert result["total"] == 2  # D-003 не включён (maintenance)
        assert result["drones"][0]["drone_id"] == "D-001"
        assert result["drones"][0]["location"]["lat"] == 55.7558
        assert result["drones"][1]["drone_id"] == "D-002"
    
    def test_get_available_drones_filters_critical_issues(self, drone_manager, mock_bus):
        """Фильтрация дронов с критическими проблемами."""
        mock_bus.request.return_value = {
            "status": "ok",
            "drones": [
                {"drone_id": "D-001", "status": "landed", "battery_level": "85.0", "port_id": "P-01", "issues": []},
                {"drone_id": "D-002", "status": "landed", "battery_level": "5.0", "port_id": "P-02", "issues": ["battery_critical"]},
                {"drone_id": "D-003", "status": "landed", "battery_level": "90.0", "port_id": "P-03", "issues": ["motor_fault"]}
            ]
        }
        
        message = {"payload": {}}
        result = drone_manager._handle_get_available_drones(message)
        
        assert result["status"] == "ok"
        assert result["total"] == 1  # Только D-001 доступен
        assert result["drones"][0]["drone_id"] == "D-001"
    
    def test_get_available_drones_registry_unavailable(self, drone_manager, mock_bus):
        """Обработка недоступности DroneRegistry."""
        mock_bus.request.return_value = None
        
        message = {"payload": {}}
        result = drone_manager._handle_get_available_drones(message)
        
        assert result["status"] == "failed"
        assert result["error_code"] == "REGISTRY_UNAVAILABLE"
        assert result["drones"] == []

class TestLandingTakeoff:
    """Тесты посадки и взлёта."""
    
    def test_handle_request_landing_success(self, drone_manager, mock_bus):
        """Успешный запрос посадки."""
        mock_bus.request.side_effect = [
            {"status": "slot_assigned", "port_id": "P-01", "corridor": {"entry_point": "P-01-ENTRY"}},
            {"status": "registered", "drone_id": "D-001"}
        ]
        
        message = {
            "payload": {
                "drone_id": "D-001",
                "battery_level": 75.0
            }
        }
        
        result = drone_manager._handle_request_landing(message)
        
        assert result["status"] == "landing_allowed"
        assert result["port_id"] == "P-01"
        assert "corridor" in result
        mock_bus.publish.assert_called()
    
    def test_handle_request_landing_no_slots(self, drone_manager, mock_bus):
        """Запрос посадки при отсутствии слотов."""
        mock_bus.request.return_value = {"status": "denied", "error_code": "PORT_RESOURCE_BUSY"}
        
        message = {"payload": {"drone_id": "D-001", "battery_level": 75.0}}
        result = drone_manager._handle_request_landing(message)
        
        assert result["status"] == "landing_denied"
        assert result["reason"] == "No available slots"
    
    def test_handle_request_takeoff_success(self, drone_manager, mock_bus):
        """Успешный запрос взлёта."""
        mock_bus.request.return_value = {"status": "ok"}
        
        message = {"payload": {"drone_id": "D-001"}}
        result = drone_manager._handle_request_takeoff(message)
        
        assert result["status"] == "takeoff_allowed"
        assert result["drone_id"] == "D-001"
        mock_bus.request.assert_called()
        mock_bus.publish.assert_called()

class TestSelfDiagnostics:
    """Тесты самодиагностики."""
    
    def test_handle_self_diagnostics_ok(self, drone_manager, mock_bus):
        """Успешная самодиагностика."""
        mock_bus.request.return_value = {"status": "updated"}
        
        message = {
            "payload": {
                "drone_id": "D-001",
                "health": {
                    "motors": "ok",
                    "internal_temp_c": 45
                }
            }
        }
        
        result = drone_manager._handle_self_diagnostics(message)
        
        assert result["status"] == "diagnostics_received"
        assert result["issues"] == []
    
    def test_handle_self_diagnostics_motor_fault(self, drone_manager, mock_bus):
        """Обнаружение неисправности моторов."""
        mock_bus.request.return_value = {"status": "updated"}
        
        message = {
            "payload": {
                "drone_id": "D-001",
                "health": {
                    "motors": "fault_detected",
                    "internal_temp_c": 45
                }
            }
        }
        
        result = drone_manager._handle_self_diagnostics(message)
        
        assert result["status"] == "diagnostics_received"
        assert "motor_fault" in result["issues"]
    
    def test_handle_self_diagnostics_overheating(self, drone_manager, mock_bus):
        """Обнаружение перегрева."""
        mock_bus.request.return_value = {"status": "updated"}
        
        message = {
            "payload": {
                "drone_id": "D-001",
                "health": {
                    "motors": "ok",
                    "internal_temp_c": 95  # > 80°C
                }
            }
        }
        
        result = drone_manager._handle_self_diagnostics(message)
        
        assert result["status"] == "diagnostics_received"
        assert "overheating" in result["issues"]