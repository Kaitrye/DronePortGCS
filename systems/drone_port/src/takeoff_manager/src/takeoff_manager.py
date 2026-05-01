"""TakeoffManager — организация взлёта."""
import logging
from typing import Dict, Any

from sdk.base_component import BaseComponent
from broker.src.system_bus import SystemBus

from ..topics import ComponentTopics, TakeoffManagerActions

logger = logging.getLogger(__name__)


class TakeoffManager(BaseComponent):
    def __init__(self, component_id: str, name: str, bus: SystemBus):
        super().__init__(
            component_id=component_id,
            component_type="drone_port",
            topic=ComponentTopics.TAKEOFF_MANAGER,
            bus=bus,
        )
        self.name = name

    def _register_handlers(self) -> None:
        self.register_handler(TakeoffManagerActions.REQUEST_TAKEOFF, self._handle_takeoff)

    def _handle_takeoff(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")

        if not drone_id:
            return {"error": "drone_id required"}

        # 1. GET_DRONE — получаем данные дрона из реестра
        drone_response = self.bus.request(
            ComponentTopics.DRONE_REGISTRY,
            {
                "action": TakeoffManagerActions.GET_DRONE,
                "payload": {"drone_id": drone_id},
                "sender": self.component_id,
            },
            timeout=5.0,
        )

        # Проверяем ответ
        if drone_response is None:
            return {"error": "Failed to get drone information"}
        
        if "error" in drone_response:
            return {"error": drone_response["error"]}

        battery = drone_response.get("battery", 0)
        port_id = drone_response.get("port_id")

        # Преобразуем battery в число если нужно
        if isinstance(battery, str):
            try:
                battery = float(battery)
            except (TypeError, ValueError):
                battery = 0

        # 2. Проверка батареи (нужно не менее 60%)
        if battery < 60.0:
            return {"error": "Not enough battery for takeoff", "battery": battery}

        # 3. RELEASE_PORT — освобождаем порт
        if port_id:
            self.bus.publish(
                ComponentTopics.PORT_MANAGER,
                {
                    "action": TakeoffManagerActions.RELEASE_PORT,
                    "payload": {"port_id": port_id, "drone_id": drone_id},
                    "sender": self.component_id,
                }
            )

        # 4. REMOVE_DRONE — удаляем дрона из реестра
        self.bus.publish(
            ComponentTopics.DRONE_REGISTRY,
            {
                "action": TakeoffManagerActions.REMOVE_DRONE,
                "payload": {"drone_id": drone_id},
                "sender": self.component_id,
            }
        )

        logger.info("[%s] Takeoff approved: drone=%s battery=%s", self.component_id, drone_id, battery)
        return {"approved": True, "drone_id": drone_id, "battery": battery}