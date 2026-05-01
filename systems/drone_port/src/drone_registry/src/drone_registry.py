"""DroneRegistry — состояние дронов."""
import datetime
import logging
from typing import Dict, Any

import redis
from sdk.base_component import BaseComponent
from broker.src.system_bus import SystemBus

from ..topics import ComponentTopics, DroneRegistryActions

logger = logging.getLogger(__name__)


class DroneRegistry(BaseComponent):
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
        redis_host: str = "localhost",
        redis_port: int = 6379,
    ):
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
        )
        super().__init__(
            component_id=component_id,
            component_type="drone_port",
            topic=ComponentTopics.DRONE_REGISTRY,
            bus=bus,
        )
        self.name = name

    def _get_key(self, drone_id: str) -> str:
        return f"drone:{drone_id}"

    def _register_handlers(self) -> None:
        self.register_handler(DroneRegistryActions.REGISTER_DRONE, self._handle_register)
        self.register_handler(DroneRegistryActions.REMOVE_DRONE, self._handle_remove)
        self.register_handler(DroneRegistryActions.GET_AVAILABLE_DRONES, self._handle_get_available)
        self.register_handler(DroneRegistryActions.UPDATE_BATTERY, self._handle_update_battery)
        self.register_handler(DroneRegistryActions.GET_DRONE, self._handle_get_drone)

    def _handle_register(self, message: Dict[str, Any]) -> None:
        payload = message.get("payload")
        
        if not isinstance(payload, dict):
            logger.warning("[%s] Invalid payload for register_drone: %r", self.component_id, payload)
            return
            
        drone_id = payload.get("drone_id")
        if not drone_id or not str(drone_id).strip():
            logger.warning("[%s] Missing drone_id in register_drone", self.component_id)
            return

        port_id = payload.get("port_id", "")
        battery = payload.get("battery", "unknown")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.redis.hset(
            self._get_key(drone_id),
            mapping={
                "drone_id": drone_id,
                "port_id": port_id,
                "battery": battery,
                "status": "registered",
                "registered_at": now,
                "updated_at": now,
            }
        )
        logger.info("[%s] Registered drone %s on port %s", self.component_id, drone_id, port_id)

    def _handle_remove(self, message: Dict[str, Any]) -> None:
        payload = message.get("payload")
        
        if not isinstance(payload, dict):
            logger.warning("[%s] Invalid payload for remove_drone: %r", self.component_id, payload)
            return
            
        drone_id = payload.get("drone_id")
        if not drone_id or not str(drone_id).strip():
            logger.warning("[%s] Missing drone_id in remove_drone", self.component_id)
            return

        self.redis.delete(self._get_key(drone_id))
        logger.info("[%s] Removed drone %s", self.component_id, drone_id)

    def _handle_get_available(self, message: Dict[str, Any]) -> Dict[str, Any]:
        drones = []
        for key in self.redis.keys("drone:*"):
            drone = self.redis.hgetall(key)
            if not drone:
                continue
                
            battery = drone.get("battery", "unknown")
            if battery != "unknown":
                try:
                    if float(battery) >= 60.0:
                        drones.append(drone)
                except (TypeError, ValueError):
                    pass
        return {"drones": drones}

    def _handle_get_drone(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload")
        
        if not isinstance(payload, dict):
            logger.warning("[%s] Invalid payload for get_drone: %r", self.component_id, payload)
            return {"error": "Invalid payload"}

        drone_id = payload.get("drone_id")
        if not drone_id or not str(drone_id).strip():
            return {"error": "drone_id required"}

        drone = self.redis.hgetall(self._get_key(drone_id))
        if not drone:
            return {"error": "Drone not found"}

        battery = drone.get("battery")
        if battery and isinstance(battery, str):
            try:
                drone["battery"] = float(battery)
            except (TypeError, ValueError):
                pass

        return drone

    def _handle_update_battery(self, message: Dict[str, Any]) -> None:
        payload = message.get("payload")
        
        if not isinstance(payload, dict):
            logger.warning("[%s] Invalid payload for update_battery: %r", self.component_id, payload)
            return

        drone_id = payload.get("drone_id")
        battery = payload.get("battery")

        if not drone_id or not str(drone_id).strip():
            logger.warning("[%s] Missing drone_id in update_battery", self.component_id)
            return
            
        if battery is None:
            logger.warning("[%s] Missing battery in update_battery for %s", self.component_id, drone_id)
            return

        try:
            battery_val = float(battery)
        except (TypeError, ValueError):
            logger.warning("[%s] Invalid battery value for %s: %r", self.component_id, drone_id, battery)
            return

        self.redis.hset(
            self._get_key(drone_id),
            mapping={
                "battery": battery_val,
                "status": "ready" if battery_val >= 100.0 else "charging",
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        )
        logger.info("[%s] Battery update %s: %s%%", self.component_id, drone_id, battery_val)