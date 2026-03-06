"""
Тесты для PowerHealthManager.
Включают тесты для новой интеграции с телеметрией дронов.
"""
import pytest
from unittest.mock import Mock, patch
from src.state_store.src.state_store import StateStore
from src.power_health_manager.src.power_health_manager import PowerHealthManager


@pytest.fixture
def mock_state_store():
    """Мок StateStore для изоляции."""
    mock = Mock()
    mock.get_drone.return_value = None
    mock.save_drone.return_value = True
    return mock


@pytest.fixture
def power_manager(mock_state_store):
    """PowerHealthManager с моком StateStore."""
    return PowerHealthManager(mock_state_store)


def test_query_drone_self_diagnostics(power_manager):
    """Тест опроса самодиагностики дрона (заглушка)."""
    result = power_manager.query_drone_self_diagnostics("D-001")
    
    assert "motors" in result
    assert "gps_signal" in result
    assert "sensors" in result
    assert "internal_temp_c" in result
    assert result["motors"] == "ok"


def test_run_post_landing_diagnostics_with_remote_health(power_manager, mock_state_store):
    """Тест диагностики с успешным опросом телеметрии дрона."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "75.0",
        "status": "landed"
    }
    
    # Мокаем query_drone_self_diagnostics
    with patch.object(power_manager, 'query_drone_self_diagnostics') as mock_query:
        mock_query.return_value = {
            "motors": "ok",
            "gps_signal": "strong",
            "sensors": "calibrated",
            "internal_temp_c": 45
        }
        
        result = power_manager.run_post_landing_diagnostics("D-001")
        
        assert result["status"] == "diagnostics.ok"
        mock_query.assert_called_once_with("D-001")


def test_run_post_landing_diagnostics_motor_fault(power_manager, mock_state_store):
    """Тест диагностики с обнаруженной неисправностью моторов."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "75.0",
        "status": "landed"
    }
    
    with patch.object(power_manager, 'query_drone_self_diagnostics') as mock_query:
        mock_query.return_value = {
            "motors": "fault_detected",
            "gps_signal": "strong",
            "sensors": "calibrated",
            "internal_temp_c": 45
        }
        
        result = power_manager.run_post_landing_diagnostics("D-001")
        
        assert result["status"] == "diagnostics.failed"
        assert "motor_fault_detected" in result["issues"]


def test_run_post_landing_diagnostics_overheating(power_manager, mock_state_store):
    """Тест диагностики с перегревом дрона."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "75.0",
        "status": "landed"
    }
    
    with patch.object(power_manager, 'query_drone_self_diagnostics') as mock_query:
        mock_query.return_value = {
            "motors": "ok",
            "gps_signal": "strong",
            "sensors": "calibrated",
            "internal_temp_c": 95  # > 80°C
        }
        
        result = power_manager.run_post_landing_diagnostics("D-001")
        
        assert result["status"] == "diagnostics.failed"
        assert "overheating" in result["issues"]


def test_run_post_landing_diagnostics_telemetry_lost(power_manager, mock_state_store):
    """Тест диагностики при потере связи с дроном."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "75.0",
        "status": "landed"
    }
    
    with patch.object(power_manager, 'query_drone_self_diagnostics') as mock_query:
        mock_query.side_effect = Exception("Connection timeout")
        
        result = power_manager.run_post_landing_diagnostics("D-001")
        
        assert result["status"] == "diagnostics.failed"
        assert "telemetry_link_lost" in result["issues"]


def test_run_post_landing_diagnostics_combined_issues(power_manager, mock_state_store):
    """Тест диагностики с несколькими проблемами одновременно."""
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "5.0",  # < 10%
        "status": "landed"
    }
    
    with patch.object(power_manager, 'query_drone_self_diagnostics') as mock_query:
        mock_query.return_value = {
            "motors": "fault_detected",
            "gps_signal": "weak",
            "sensors": "calibrated",
            "internal_temp_c": 85  # > 80°C
        }
        
        result = power_manager.run_post_landing_diagnostics("D-001")
        
        assert result["status"] == "diagnostics.failed"
        assert "battery_critical" in result["issues"]
        assert "motor_fault_detected" in result["issues"]
        assert "overheating" in result["issues"]


def test_charge_to_threshold_success(power_manager, mock_state_store):
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "50.0",
        "status": "landed"
    }
    
    result = power_manager.charge_to_threshold(
        drone_id="D-001",
        min_battery=90.0,
        current_battery=50.0,
        departure_time_sec=3600
    )
    
    assert result["status"] == "charge.completed"
    assert result["charging_power_w"] > 0
    mock_state_store.save_drone.assert_called_once()


def test_charge_to_threshold_already_sufficient(power_manager, mock_state_store):
    result = power_manager.charge_to_threshold(
        drone_id="D-001",
        min_battery=80.0,
        current_battery=85.0,
        departure_time_sec=3600
    )
    
    assert result["status"] == "charge.not_required"


def test_auto_start_charging_if_needed_triggers(power_manager, mock_state_store):
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "70.0",
        "status": "landed"
    }
    
    result = power_manager.auto_start_charging_if_needed("D-001")
    
    assert result["status"] == "charging.started"
    mock_state_store.save_drone.assert_called_once()


def test_auto_start_charging_if_needed_not_required(power_manager, mock_state_store):
    mock_state_store.get_drone.return_value = {
        "drone_id": "D-001",
        "battery_level": "90.0",
        "status": "landed"
    }
    
    result = power_manager.auto_start_charging_if_needed("D-001")
    
    assert result["status"] == "charging.not_required"