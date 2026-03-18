"""
DroneportOrchestrator — тонкий мост между Эксплуатантом и DroneRegistry.
"""
import datetime
from typing import Dict, Any
from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.drone_port.src.droneport_orchestrator.topics import DroneportOrchestratorTopics


class DroneportOrchestrator(BaseComponent):
    """
    Перенаправляет запросы от Эксплуатанта в DroneRegistry.
    """
    
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
    ):
        self.topics = DroneportOrchestratorTopics(component_id)
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic,
            bus=bus,
        )
        self.name = name
        print(f"DroneportOrchestrator '{name}' initialized")

    def _register_handlers(self) -> None:
        self.register_handler("fleet_report", self._handle_fleet_report)
        self.register_handler("start_charging", self._handle_start_charging)

    def _handle_fleet_report(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запрос отчета о флоте.
        
        Перенаправляет в DroneRegistry и возвращает ответ.
        """
        # Перенаправляем в Registry
        response = self.bus.request(
            "v1.droneport.dp-001.registry.get_aggregated_status",
            {
                "request_id": message.get("request_id"),
                "payload": message.get("payload", {})
            },
            timeout=5.0
        )
        
        if not response:
            return {
                "status": "error",
                "reason": "Registry not responding"
            }
        
        return response

    def _handle_start_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Команда на запуск зарядки.
        
        Эксплуатант шлет в Orchestrator, Orchestrator перенаправляет в Registry.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {
                "status": "error",
                "reason": "Missing drone_id"
            }
        
        # Перенаправляем в Registry
        response = self.bus.request(
            "v1.droneport.dp-001.registry.start_charging",
            {
                "request_id": message.get("request_id"),
                "payload": payload
            },
            timeout=5.0
        )
        
        if not response:
            return {
                "status": "error",
                "reason": "Registry not responding"
            }
        
        return response