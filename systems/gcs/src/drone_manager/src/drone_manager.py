"""DroneManagerComponent для взаимодействия с дронами"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict

from broker.src.system_bus import SystemBus
from sdk.base_component import BaseComponent
from systems.gcs.topics import DroneActions, DroneTopics
from systems.gcs.src.contracts import DroneStatus, MissionStatus
from systems.gcs.src.drone_manager.topics import ComponentTopics, DroneManagerActions
from systems.gcs.src.mission_store.topics import MissionStoreActions
from systems.gcs.src.drone_store.topics import DroneStoreActions


class DroneManagerComponent(BaseComponent):
    def __init__(self, component_id: str, bus: SystemBus):
        self._telemetry_poll_interval_s = 0.5
        self._telemetry_pollers: dict[str, tuple[threading.Thread, threading.Event]] = {}
        super().__init__(
            component_id=component_id,
            component_type="gcs_drone_manager",
            topic=ComponentTopics.GCS_DRONE,
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(DroneManagerActions.MISSION_UPLOAD, self._handle_mission_upload)
        self.register_handler(DroneManagerActions.MISSION_START, self._handle_mission_start)

    def _proxy_request_drone(
        self,
        target_topic: str,
        target_action: str,
        data: Dict[str, Any],
        correlation_id: str | None = None,
    ) -> Dict[str, Any] | None:
        message = {
            "action": DroneActions.PROXY_REQUEST,
            "sender": ComponentTopics.GCS_DRONE,
            "payload": {
                "target": {
                    "topic": target_topic,
                    "action": target_action,
                },
                "data": data,
            },
        }
        if correlation_id:
            message["correlation_id"] = correlation_id

        response = self.bus.request(
            DroneTopics.SECURITY_MONITOR,
            message,
            timeout=10.0,
        )
        if not isinstance(response, dict):
            return None
        target_response = response.get("target_response")
        return target_response if isinstance(target_response, dict) else response

    def _response_payload(self, response: Dict[str, Any] | None) -> Dict[str, Any] | None:
        if not isinstance(response, dict):
            return None
        payload = response.get("payload")
        return payload if isinstance(payload, dict) else response

    def _response_ok(self, response: Dict[str, Any] | None) -> bool:
        payload = self._response_payload(response)
        if not isinstance(payload, dict):
            return False
        if response.get("success") is False:
            return False
        return bool(payload.get("ok"))

    def _handle_mission_upload(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = payload.get("mission_id")
        drone_id = payload.get("drone_id")
        wpl = payload.get("wpl")

        upload_response = self._proxy_request_drone(
            DroneTopics.MISSION_HANDLER,
            DroneActions.LOAD_MISSION,
            {
                "mission_id": mission_id,
                "wpl_content": wpl,
            },
            correlation_id=correlation_id,
        )
        if not self._response_ok(upload_response):
            return None

        mission_update_message = {
            "action": MissionStoreActions.UPDATE_MISSION,
            "sender": self.component_id,
            "payload": {
                "mission_id": mission_id,
                "fields": {
                    "assigned_drone": drone_id,
                    "status": MissionStatus.ASSIGNED,
                },
            },
        }
        if correlation_id:
            mission_update_message["correlation_id"] = correlation_id

        self.bus.publish(
            ComponentTopics.GCS_MISSION_STORE,
            mission_update_message,
        )

        drone_update_message = {
            "action": DroneStoreActions.UPDATE_DRONE,
            "sender": self.component_id,
            "payload": {
                "drone_id": drone_id,
                "status": DroneStatus.RESERVED,
            },
        }
        if correlation_id:
            drone_update_message["correlation_id"] = correlation_id

        self.bus.publish(
            ComponentTopics.GCS_DRONE_STORE,
            drone_update_message,
        )

        return None

    def _extract_telemetry(self, response: Any) -> Dict[str, Any] | None:
        if not isinstance(response, dict):
            return None

        if isinstance(response.get("target_response"), dict):
            return self._extract_telemetry(response["target_response"])

        if isinstance(response.get("payload"), dict) and isinstance(response["payload"].get("telemetry"), dict):
            return response["payload"]["telemetry"]

        if isinstance(response.get("payload"), dict):
            payload = response["payload"]
            navigation = payload.get("navigation")
            if isinstance(navigation, dict):
                telemetry: Dict[str, Any] = {}
                if navigation.get("lat") is not None:
                    telemetry["latitude"] = navigation.get("lat")
                if navigation.get("lon") is not None:
                    telemetry["longitude"] = navigation.get("lon")
                if navigation.get("alt_m") is not None:
                    telemetry["altitude"] = navigation.get("alt_m")
                motors = payload.get("motors")
                if isinstance(motors, dict) and motors.get("battery") is not None:
                    telemetry["battery"] = motors.get("battery")
                return telemetry or None

        if isinstance(response.get("telemetry"), dict):
            return response["telemetry"]

        return None

    def _save_telemetry(self, telemetry: Dict[str, Any], correlation_id: str | None = None) -> None:
        telemetry_message = {
            "action": DroneStoreActions.SAVE_TELEMETRY,
            "sender": self.component_id,
            "payload": {
                "telemetry": telemetry,
            },
        }
        if correlation_id:
            telemetry_message["correlation_id"] = correlation_id

        self.bus.publish(ComponentTopics.GCS_DRONE_STORE, telemetry_message)

    def _poll_telemetry_loop(self, drone_id: str, stop_event: threading.Event) -> None:
        while not stop_event.wait(self._telemetry_poll_interval_s):
            if not self._running:
                break

            response = self.bus.request(
                DroneTopics.SECURITY_MONITOR,
                {
                    "action": DroneActions.PROXY_REQUEST,
                    "sender": ComponentTopics.GCS_DRONE,
                    "payload": {
                        "target": {
                            "topic": DroneTopics.TELEMETRY,
                            "action": DroneActions.TELEMETRY_GET,
                        },
                        "data": {
                        "drone_id": drone_id,
                        },
                    },
                },
                timeout=5.0,
            )

            telemetry = self._extract_telemetry(response)
            if telemetry is None:
                continue

            telemetry.setdefault("drone_id", drone_id)
            self._save_telemetry(telemetry)

    def _start_telemetry_polling(self, drone_id: str) -> None:
        active = self._telemetry_pollers.get(drone_id)
        if active and active[0].is_alive():
            return

        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._poll_telemetry_loop,
            args=(drone_id, stop_event),
            daemon=True,
            name=f"{self.component_id}-telemetry-{drone_id}",
        )
        self._telemetry_pollers[drone_id] = (thread, stop_event)
        thread.start()

    def stop(self):
        for thread, stop_event in self._telemetry_pollers.values():
            stop_event.set()
            thread.join(timeout=1.0)
        self._telemetry_pollers.clear()
        super().stop()

    def _handle_mission_start(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = payload.get("mission_id")
        drone_id = payload.get("drone_id")

        start_response = self._proxy_request_drone(
            DroneTopics.AUTOPILOT,
            DroneActions.CMD,
            {
                "command": "START",
            },
            correlation_id=correlation_id,
        )
        if not self._response_ok(start_response):
            return None
        
        mission_update_message = {
            "action": MissionStoreActions.UPDATE_MISSION,
            "sender": self.component_id,
            "payload": {
                "mission_id": mission_id,
                "fields": {
                    "status": MissionStatus.RUNNING,
                },
            },
        }
        if correlation_id:
            mission_update_message["correlation_id"] = correlation_id

        self.bus.publish(
            ComponentTopics.GCS_MISSION_STORE,
            mission_update_message,
        )

        drone_update_message = {
            "action": DroneStoreActions.UPDATE_DRONE,
            "sender": self.component_id,
            "payload": {
                "drone_id": drone_id,
                "status": DroneStatus.BUSY,
            },
        }
        if correlation_id:
            drone_update_message["correlation_id"] = correlation_id

        self.bus.publish(
            ComponentTopics.GCS_DRONE_STORE,
            drone_update_message,
        )

        if drone_id:
            self._start_telemetry_polling(drone_id)

        return None
