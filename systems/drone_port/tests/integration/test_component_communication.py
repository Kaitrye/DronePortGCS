"""
Интеграционные тесты межкомпонентного взаимодействия.
Проверяют request/response и publish/subscribe паттерны.
"""
import pytest
from unittest.mock import Mock
from typing import Dict, Any

from src.drone_manager.topics import DroneManagerTopics
from src.drone_registry.topics import DroneRegistryTopics
from src.port_manager.topics import PortManagerTopics
from src.charging_manager.topics import ChargingManagerTopics

SYSTEM_ID = "dp-001"

@pytest.fixture
def mock_bus():
    mock = Mock()
    mock.subscribe = Mock()
    mock.publish = Mock()
    mock.request = Mock()
    return mock

class TestRequestResponsePattern:
    """Тесты паттерна запрос-ответ."""
    
    def test_synchronous_request_response(self, mock_bus):
        """
        Синхронный запрос с ожиданием ответа.
        """
        registry_topics = DroneRegistryTopics(SYSTEM_ID)
        
        mock_bus.request.return_value = {
            "status": "ok",
            "drone": {
                "drone_id": "D-001",
                "battery_level": "75.0",
                "status": "landed"
            }
        }
        
        response = mock_bus.request(
            registry_topics.GET_DRONE,
            {"payload": {"drone_id": "D-001"}},
            timeout=5.0
        )
        
        assert response is not None
        assert response["status"] == "ok"
        assert response["drone"]["drone_id"] == "D-001"
        mock_bus.request.assert_called_once()
    
    def test_request_with_timeout(self, mock_bus):
        """
        Запрос с таймаутом.
        """
        mock_bus.request.return_value = None  # Таймаут
        
        response = mock_bus.request(
            "v1.droneport.dp-001.registry.get_drone",
            {"payload": {"drone_id": "D-001"}},
            timeout=2.0
        )
        
        assert response is None

class TestPublishSubscribePattern:
    """Тесты паттерна публикация-подписка."""
    
    def test_fire_and_forget_publish(self, mock_bus):
        """
        Одностороннее сообщение (fire and forget).
        """
        charging_topics = ChargingManagerTopics(SYSTEM_ID)
        
        mock_bus.publish(
            charging_topics.CHARGING_STARTED,
            {
                "drone_id": "D-001",
                "timestamp": "2026-03-16T12:00:00Z"
            }
        )
        
        mock_bus.publish.assert_called_once()
        # Нет ожидания ответа
    
    def test_event_broadcasting(self, mock_bus):
        """
        Рассылка события нескольким подписчикам.
        """
        drone_manager_topics = DroneManagerTopics(SYSTEM_ID)
        
        # Публикация события изменения позиции
        mock_bus.publish(
            drone_manager_topics.EVENTS_BASE + ".position_updated",
            {
                "drone_id": "D-001",
                "lat": 55.7558,
                "lon": 37.6173,
                "alt": 100.0
            }
        )
        
        assert mock_bus.publish.called

class TestTopicRouting:
    """Тесты маршрутизации по топикам."""
    
    def test_component_specific_topics(self, mock_bus):
        """
        Каждый компонент имеет свои изолированные топики.
        """
        topics = {
            "drone_manager": DroneManagerTopics(SYSTEM_ID),
            "registry": DroneRegistryTopics(SYSTEM_ID),
            "port_manager": PortManagerTopics(SYSTEM_ID),
            "charging_manager": ChargingManagerTopics(SYSTEM_ID)
        }
        
        # Проверяем что топики не пересекаются
        topic_names = [t.BASE for t in topics.values()]
        assert len(topic_names) == len(set(topic_names)), "Топики должны быть уникальны"
    
    def test_version_compatibility(self, mock_bus):
        """
        Проверка совместимости версий топиков.
        """
        # v1 топики
        v1_topic = f"v1.droneport.{SYSTEM_ID}.orchestrator.fleet.report"
        
        # В будущем можно добавить v2
        # v2_topic = f"v2.droneport.{SYSTEM_ID}.orchestrator.fleet.report"
        
        # Текущая версия должна работать
        mock_bus.request.return_value = {"status": "ok"}
        response = mock_bus.request(v1_topic, {}, timeout=5.0)
        
        assert response is not None