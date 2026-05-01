"""ChargingManager — зарядка дронов."""
import logging
import threading
import time
from typing import Dict, Any

from sdk.base_component import BaseComponent
from broker.src.system_bus import SystemBus

from ..topics import ComponentTopics, ChargingManagerActions

logger = logging.getLogger(__name__)


class ChargingManager(BaseComponent):
    def __init__(self, component_id: str, name: str, bus: SystemBus):
        super().__init__(
            component_id=component_id,
            component_type="drone_port",
            topic=ComponentTopics.CHARGING_MANAGER,
            bus=bus,
        )
        self.name = name
        self._charging_rate_pct_per_s = 2.0

    def _register_handlers(self) -> None:
        self.register_handler(ChargingManagerActions.START_CHARGING, self._handle_start_charging)

    def _simulate_charging(self, drone_id: str, battery: float) -> None:
        current = max(0.0, min(battery, 100.0))

        while current < 100.0:
            time.sleep(0.5)
            current = min(100.0, current + self._charging_rate_pct_per_s * 0.5)
            current = round(current, 2)

            self.bus.publish(
                ComponentTopics.DRONE_REGISTRY,
                {
                    "action": "update_battery",
                    "payload": {"drone_id": drone_id, "battery": current},
                    "sender": self.component_id,
                }
            )
            logger.info("[%s] Charging %s: %s%%", self.component_id, drone_id, current)

    def _handle_start_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        battery = payload.get("battery", 0.0)

        if not drone_id:
            return {"error": "drone_id required"}

        logger.info("[%s] Start charging %s from %s%%", self.component_id, drone_id, battery)
        threading.Thread(
            target=self._simulate_charging,
            args=(drone_id, battery),
            daemon=True,
        ).start()
        return {"started": True, "drone_id": drone_id}