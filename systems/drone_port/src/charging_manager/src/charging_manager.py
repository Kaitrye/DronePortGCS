"""
ChargingManager — логика зарядки дронов.
"""
import datetime
from typing import Dict, Any
from sdk.base_component import BaseComponent
from broker.src.system_bus import SystemBus
from systems.drone_port.src.charging_manager.topics import ChargingManagerTopics


class ChargingManager(BaseComponent):
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
    ):
        self.topics = ChargingManagerTopics(component_id)
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic,
            bus=bus,
        )
        self.name = name
        print(f"ChargingManager '{name}' initialized")

    def _register_handlers(self) -> None:
        self.register_handler("start_charging", self._handle_start_charging)

    def _handle_start_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запуск зарядки дрона.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {
                "status": "error",
                "reason": "Missing drone_id"
            }
        
        # Публикуем событие о начале зарядки
        # DroneRegistry подписан и обновит статус
        self.bus.publish(
            self.topics.CHARGING_STARTED,
            {
                "event": "charging_started",
                "drone_id": drone_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )
        
        return {
            "status": "started",
            "drone_id": drone_id
        }