"""
DroneportOrchestrator — система, оркестрирующая компоненты.
"""
import datetime
from typing import Dict, Any, Optional
from sdk.base_component import BaseComponent
from broker.mqtt.mqtt_system_bus import MQTTSystemBus
from systems.drone_port.src.droneport_orchestrator.topics import DroneportOrchestratorTopics
from systems.drone_port.src.drone_registry.topics import DroneRegistryTopics
from systems.drone_port.src.charging_manager.topics import ChargingManagerTopics


class DroneportOrchestrator(BaseComponent):
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: MQTTSystemBus,
    ):
        self.topics = DroneportOrchestratorTopics(component_id)
        self.registry_topics = DroneRegistryTopics(component_id)
        self.charging_topics = ChargingManagerTopics(component_id)
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic, 
            bus=bus,
        )
        self.name = name
        print(f"DroneportOrchestrator '{name}' initialized (routing only)")

    def _register_handlers(self) -> None:
        """Регистрация ТОЛЬКО команд от Эксплуатанта (по action, не по топику!)."""
        self.register_handler("fleet_report", self._handle_fleet_report)
        self.register_handler("health_check", self._handle_health_check)

    def _handle_fleet_report(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Запрос агрегированных данных о флоте через DroneRegistry (Facade)."""
        request_id = message.get("request_id")
        
        response = self.bus.request(
            self.registry_topics.GET_AGGREGATED_FLEET_STATUS,
            {"request_id": request_id},
            timeout=10.0
        )
        
        if not response:
            return {
                "status": "failed",
                "error_code": "TIMEOUT",
                "reason": "DroneRegistry did not respond"
            }
        
        return {
            "status": "report_generated",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "payload": response.get("payload", {})
        }

    def _handle_health_check(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "health.ok",
            "timestamp": message.get("timestamp"),
            "component_id": self.component_id
        }

    def start_charging(self, drone_id: str) -> None:
        """
        ✅ Publish-only: запуск зарядки дрона (без ответа).
        Отправляет команду в ChargingManager напрямую.
        """
        self.bus.publish(
            self.charging_topics.START_CHARGING,
            {
                "action": "start_charging",
                "payload": {"drone_id": drone_id},
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )
        print(f"[{self.component_id}] Published START_CHARGING for drone: {drone_id}")

    def publish_sitl_positions(self, positions: Dict[str, Any]) -> None:
        """Публикация позиций дронов в SITL"""
        self.bus.publish(
            self.topics.SITL_POSITIONS,
            {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "payload": positions
            }
        )