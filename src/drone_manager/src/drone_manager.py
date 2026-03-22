"""DroneManagerComponent для взаимодействия с дронами"""

from __future__ import annotations

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
        super().__init__(
            component_id=component_id,
            component_type="gcs_drone_manager",
            topic=ComponentTopics.GCS_DRONE,
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(DroneManagerActions.MISSION_UPLOAD, self._handle_mission_upload)
        self.register_handler(DroneManagerActions.MISSION_START, self._handle_mission_start)
        self.register_handler(DroneManagerActions.TELEMETRY_SAVE, self._handle_telemetry_save)


    def _handle_mission_upload(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = payload.get("mission_id")
        drone_id = payload.get("drone_id")
        wpl = payload.get("wpl")

        upload_message = {
            "action": DroneActions.UPLOAD_MISSION,
            "sender": self.component_id,
            "payload": {
                "mission_id": mission_id,
                "mission": wpl,
            },
        }
        if correlation_id:
            upload_message["correlation_id"] = correlation_id

        self.bus.publish(
            DroneTopics.DRONE,
            upload_message,
        )

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

    def _handle_telemetry_save(self, message: Dict[str, Any]) -> None:
        correlation_id = message.get("correlation_id")
        payload = message.get("payload")

        telemetry_message = {
            "action": DroneStoreActions.SAVE_TELEMETRY,
            "sender": self.component_id,
            "payload": payload,
        }
        if correlation_id:
            telemetry_message["correlation_id"] = correlation_id

        self.bus.publish(
            ComponentTopics.GCS_DRONE_STORE,
            telemetry_message,
        )

    def _handle_mission_start(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = payload.get("mission_id")
        drone_id = payload.get("drone_id")

        start_message = {
            "action": DroneActions.MISSION_START,
            "sender": self.component_id,
            "payload": {},
        }
        if correlation_id:
            start_message["correlation_id"] = correlation_id

        self.bus.publish(
            DroneTopics.DRONE,
            start_message,
        )
        
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

        return None
