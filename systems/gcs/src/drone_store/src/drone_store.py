from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from broker.src.system_bus import SystemBus
from sdk.base_redis_store_component import BaseRedisStoreComponent
from systems.gcs.src.drone_store.topics import ComponentTopics, DroneStoreActions


class DroneStoreComponent(BaseRedisStoreComponent):
    @staticmethod
    def _normalize_drone_id(value: Any) -> Optional[str]:
        """Возвращает непустой id или None, если значение использовать нельзя."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        if isinstance(value, int):
            return str(value)
        return None

    def __init__(self, component_id: str, bus: SystemBus):
        self.initial_fleet: Dict[str, Dict[str, Any]] = {}
        super().__init__(
            component_id=component_id,
            component_type="gcs_drone_store",
            topic=ComponentTopics.GCS_DRONE_STORE,
            bus=bus,
            redis_db_env="DRONE_STORE_REDIS_DB",
            redis_default_db=1,
        )

    def _drone_key(self, drone_id: str) -> str:
        return f"gcs:drone:{drone_id}"

    def _all_drones_key(self) -> str:
        return "gcs:drones:all"

    def _available_drones_key(self) -> str:
        return "gcs:drones:available"

    def _read_drone(self, drone_id: str) -> Optional[Dict[str, Any]]:
        nid = self._normalize_drone_id(drone_id)
        if nid is None:
            return None
        raw = self.redis_client.get(self._drone_key(nid))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _write_drone(self, drone_id: str, state: Dict[str, Any]) -> None:
        nid = self._normalize_drone_id(drone_id)
        if nid is None:
            return
        self.redis_client.set(self._drone_key(nid), json.dumps(state, ensure_ascii=False))
        self.redis_client.sadd(self._all_drones_key(), nid)
        if state.get("status") == "available":
            self.redis_client.sadd(self._available_drones_key(), nid)
        else:
            self.redis_client.srem(self._available_drones_key(), nid)

    def _all_drone_ids(self) -> Set[str]:
        return set(self.redis_client.smembers(self._all_drones_key()))

    def _available_drone_ids(self) -> Set[str]:
        return set(self.redis_client.smembers(self._available_drones_key()))

    def _update_drone_from_telemetry(self, drone_id: str, telemetry: Dict[str, Any], allow_register: bool = True) -> None:
        nid = self._normalize_drone_id(drone_id)
        if nid is None:
            return

        drone_state = self._read_drone(nid)

        if drone_state is None:
            drone_state = {}
            now = datetime.now(timezone.utc).isoformat()

            drone_state.setdefault("connected_at", now)
            drone_state["status"] = "connected"

        if "battery" in telemetry:
            raw_battery = telemetry.get("battery")
            if raw_battery is not None:
                try:
                    drone_state["battery"] = int(raw_battery)
                except (TypeError, ValueError):
                    pass

        latitude = telemetry.get("latitude")
        longitude = telemetry.get("longitude")
        altitude = telemetry.get("altitude")
        if latitude is not None and longitude is not None:
            drone_state["last_position"] = {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
            }

        self._write_drone(nid, drone_state)
        return None


    def _register_handlers(self):
        self.register_handler(DroneStoreActions.UPDATE_DRONE, self._handle_update_drone)
        self.register_handler(DroneStoreActions.SAVE_TELEMETRY, self._handle_save_telemetry)


    def _handle_save_telemetry(self, message: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(message, dict):
            return None
        payload = message.get("payload")
        if not isinstance(payload, dict):
            return None
        telemetry = payload.get("telemetry")
        if not isinstance(telemetry, dict):
            return None
        drone_id = self._normalize_drone_id(telemetry.get("drone_id"))
        if drone_id is None:
            return None

        self._update_drone_from_telemetry(drone_id, telemetry)
        return None

    def _handle_update_drone(self, message: Any) -> None:
        if not isinstance(message, dict):
            return None
        payload = message.get("payload")
        if not isinstance(payload, dict):
            return None
        drone_id = self._normalize_drone_id(payload.get("drone_id"))
        if drone_id is None:
            return None
        status = payload.get("status")

        drone_state = self._read_drone(drone_id) or {}
        drone_state["status"] = status

        self._write_drone(drone_id, drone_state)

        return None
