"""
Тесты компонента DroneportOrchestrator (координация компонентов).
Проверяют маршрутизацию команд и агрегацию данных.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.droneport_orchestrator.src.orchestrator import DroneportOrchestrator
from src.state_store.src.state_store import StateStore


@pytest.fixture
def mock_bus():
    """Мок SystemBus."""
    mock = Mock()
    mock.subscribe = Mock()
    mock.publish = Mock()
    return mock


@pytest.fixture
def mock_state_store():
    """Мок StateStore."""
    mock = Mock()
    mock.list_drones.return_value = []
    mock.get_all_ports_status.return_value = []
    return mock


@pytest.fixture
def orchestrator(mock_bus, mock_state_store):
    """DroneportOrchestrator с моками."""
    orch = DroneportOrchestrator(
        system_id="droneport-01",
        name="TestPort",
        bus=mock_bus
    )
    orch.state = mock_state_store
    # Мокаем компоненты
    orch.port_manager = Mock()
    orch.power_health = Mock()
    orch.drone_registry = Mock()
    return orch


# === ТЕСТЫ ДЛЯ НОВЫХ МЕТОДОВ ===

def test_handle_operator_report_request(orchestrator, mock_state_store):
    """Тест обработки запроса отчёта для эксплуатанта."""
    mock_state_store.get_aggregated_fleet_status.return_value = {
        "fleet": {"total": 5, "charging": 2, "ready": 3, "issues": 0},
        "ports": {"total": 4, "occupied": 2, "maintenance": 0},
        "alerts": []
    }
    
    message = {
        "payload": {"request_id": "REQ-001"},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    result = orchestrator._handle_operator_report_request(message)
    
    assert result["status"] == "report_generated"
    assert "timestamp" in result
    assert "payload" in result
    assert result["payload"]["fleet"]["total"] == 5
    assert result["droneport_id"] == "droneport-01"
    assert result["droneport_name"] == "TestPort"
    mock_state_store.get_aggregated_fleet_status.assert_called_once()


def test_handle_operator_report_request_with_alerts(orchestrator, mock_state_store):
    """Тест отчёта с предупреждениями о проблемах."""
    mock_state_store.get_aggregated_fleet_status.return_value = {
        "fleet": {"total": 5, "charging": 2, "ready": 2, "issues": 1},
        "ports": {"total": 4, "occupied": 2, "maintenance": 1},
        "alerts": [{"drone_id": "D-003", "issue": "battery_critical"}]
    }
    
    message = {"payload": {"request_id": "REQ-002"}}
    
    result = orchestrator._handle_operator_report_request(message)
    
    assert len(result["payload"]["alerts"]) == 1
    assert result["payload"]["alerts"][0]["drone_id"] == "D-003"


def test_get_status_with_ports(orchestrator, mock_state_store):
    """Тест получения статуса дронопорта с подсчётом портов."""
    mock_state_store.get_all_ports_status.return_value = [
        {"port_id": "P-01", "drone_id": "D-001"},
        {"port_id": "P-02", "drone_id": "D-002"},
        {"port_id": "P-03", "drone_id": ""},
        {"port_id": "P-04", "drone_id": ""}
    ]
    orchestrator.drone_registry.list_all_drones.return_value = [
        {"drone_id": "D-001"},
        {"drone_id": "D-002"}
    ]
    
    status = orchestrator.get_status()
    
    assert status["drones_total"] == 2
    assert status["ports_occupied"] == 2
    assert status["ports_total"] == 4
    assert status["name"] == "TestPort"


def test_handle_request_landing_slot_delegation(orchestrator):
    """Тест делегирования запроса посадки в PortManager."""
    orchestrator.port_manager.request_landing_slot.return_value = {
        "status": "slot_assigned",
        "port_id": "P-01",
        "drone_id": "D-001"
    }
    
    message = {
        "payload": {"drone_id": "D-001", "preferred_ports": ["P-01", "P-02"]}
    }
    
    result = orchestrator._handle_request_landing_slot(message)
    
    assert result["status"] == "slot_assigned"
    assert result["port_id"] == "P-01"
    orchestrator.port_manager.request_landing_slot.assert_called_once_with(
        "D-001",
        ["P-01", "P-02"]
    )


def test_handle_dock_flow(orchestrator):
    """Тест полного потока посадки: диагностика + зарядка."""
    orchestrator.power_health.run_post_landing_diagnostics.return_value = {
        "status": "diagnostics.ok",
        "drone_id": "D-001"
    }
    orchestrator.power_health.auto_start_charging_if_needed.return_value = {
        "status": "charging.started",
        "drone_id": "D-001"
    }
    
    message = {"payload": {"drone_id": "D-001"}}
    
    result = orchestrator._handle_dock(message)
    
    assert result["status"] == "docked"
    orchestrator.power_health.run_post_landing_diagnostics.assert_called_once_with("D-001")
    orchestrator.power_health.auto_start_charging_if_needed.assert_called_once_with("D-001")


def test_handle_dock_diagnostics_failed(orchestrator):
    """Тест посадки с неудачной диагностикой."""
    orchestrator.power_health.run_post_landing_diagnostics.return_value = {
        "status": "diagnostics.failed",
        "drone_id": "D-001",
        "issues": ["battery_critical"]
    }
    
    message = {"payload": {"drone_id": "D-001"}}
    
    result = orchestrator._handle_dock(message)
    
    assert result["status"] == "docked"
    # auto_start_charging_if_needed не должен вызываться при failed diagnostics
    orchestrator.power_health.auto_start_charging_if_needed.assert_not_called()


def test_handle_reserve_slots_batch(orchestrator):
    """Тест резервирования нескольких слотов одновременно."""
    orchestrator.port_manager.reserve_slot.side_effect = [
        {"status": "reserved", "port_id": "P-01", "drone_id": "D-001"},
        {"status": "reserved", "port_id": "P-02", "drone_id": "D-002"},
        {"status": "rejected", "error_code": "PORT_RESOURCE_BUSY", "drone_id": "D-003"}
    ]
    
    message = {
        "payload": {
            "drone_ids": ["D-001", "D-002", "D-003"],
            "mission_window": {"start": "2026-02-27T12:00:00Z", "end": "2026-02-27T13:00:00Z"}
        }
    }
    
    result = orchestrator._handle_reserve_slots(message)
    
    assert result["status"] == "partial"
    assert len(result["results"]) == 3
    assert orchestrator.port_manager.reserve_slot.call_count == 3


def test_handle_health_check(orchestrator):
    """Тест проверки здоровья системы."""
    message = {"timestamp": "2026-02-27T12:00:00Z"}
    
    result = orchestrator._handle_health_check(message)
    
    assert result["status"] == "health.ok"
    assert result["timestamp"] == message["timestamp"]


def test_orchestrator_initialization(orchestrator, mock_bus):
    """Тест инициализации оркестратора."""
    assert orchestrator.system_id == "droneport-01"
    assert orchestrator.name == "TestPort"
    assert orchestrator.bus == mock_bus
    assert orchestrator.state is not None
    assert orchestrator.port_manager is not None
    assert orchestrator.power_health is not None
    assert orchestrator.drone_registry is not None