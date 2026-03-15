"""
DroneportOrchestrator — ТОЛЬКО маршрутизация к DroneRegistry (Facade).
НЕ знает о других компонентах напрямую.
"""
import datetime
from typing import Dict, Any, Optional
from shared.base_system import BaseSystem
from broker.system_bus import SystemBus
from src.droneport_orchestrator.topics import DroneportOrchestratorTopics
from src.drone_registry.topics import DroneRegistryTopics

class DroneportOrchestrator(BaseSystem):
    def __init__(
        self,
        system_id: str,
        name: str,
        bus: SystemBus,
        health_port: Optional[int] = None,
    ):
        self.topics = DroneportOrchestratorTopics(system_id)
        self.registry_topics = DroneRegistryTopics(system_id)
        
        super().__init__(
            system_id=system_id,
            system_type="droneport",
            topic=self.topics.BASE,
            bus=bus,
            health_port=health_port,
        )
        self.name = name
        print(f"DroneportOrchestrator '{name}' initialized (routing only)")
        
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Регистрация ТОЛЬКО команд от Эксплуатанта"""
        self.register_handler(self.topics.FLEET_REPORT, self._handle_fleet_report)
        self.register_handler(self.topics.HEALTH_CHECK, self._handle_health_check)

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
            "timestamp": datetime.utcnow().isoformat(),
            "payload": response.get("payload", {})
        }

    def _handle_health_check(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "health.ok",
            "timestamp": message.get("timestamp"),
            "system_id": self.system_id
        }

    def publish_sitl_positions(self, positions: Dict[str, Any]) -> None:
        """Публикация позиций дронов в SITL"""
        self.bus.publish(
            self.topics.SITL_POSITIONS,
            {
                "timestamp": datetime.utcnow().isoformat(),
                "payload": positions
            }
        )