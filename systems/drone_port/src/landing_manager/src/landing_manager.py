"""LandingManager — организация посадки."""
import logging
from typing import Dict, Any

from sdk.base_component import BaseComponent
from broker.src.system_bus import SystemBus

from ..topics import ComponentTopics, LandingManagerActions

logger = logging.getLogger(__name__)


class LandingManager(BaseComponent):
    def __init__(self, component_id: str, name: str, bus: SystemBus):
        super().__init__(
            component_id=component_id,
            component_type="drone_port",
            topic=ComponentTopics.LANDING_MANAGER,
            bus=bus,
        )
        self.name = name

    def _register_handlers(self) -> None:
        self.register_handler(LandingManagerActions.REQUEST_LANDING, self._handle_landing)

    def _handle_landing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        battery = payload.get("battery", 0.0)

        if not drone_id:
            return {"error": "drone_id required"}

        # 1. OCCUPY_PORT — резервируем порт
        occupy_response = self.bus.request(
            ComponentTopics.PORT_MANAGER,
            {
                "action": LandingManagerActions.OCCUPY_PORT,
                "payload": {"drone_id": drone_id},
                "sender": self.component_id,
            },
            timeout=5.0,
        )

        port_id = (occupy_response or {}).get("port_id")
        if not port_id:
            return {"error": "No free ports"}

        # 2. REGISTER_DRONE — регистрируем дрона
        self.bus.publish(
            ComponentTopics.DRONE_REGISTRY,
            {
                "action": LandingManagerActions.REGISTER_DRONE,
                "payload": {"drone_id": drone_id, "port_id": port_id, "battery": battery},
                "sender": self.component_id,
            }
        )

        # 3. START_CHARGING — запускаем зарядку если нужно
        if battery < 100.0:
            self.bus.publish(
                ComponentTopics.CHARGING_MANAGER,
                {
                    "action": LandingManagerActions.START_CHARGING,
                    "payload": {"drone_id": drone_id, "battery": battery},
                    "sender": self.component_id,
                }
            )

        logger.info("[%s] Landing completed: drone=%s port=%s", self.component_id, drone_id, port_id)
        return {"approved": True, "port_id": port_id, "drone_id": drone_id}