"""DroneManagerComponent для взаимодействия с дронами"""

from __future__ import annotations

from typing import Any, Dict, Optional

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent
from systems.gcs.src.contracts import DroneStatus, MissionStatus
from systems.gcs.src.drone_manager.topics import ComponentTopics, DroneManagerActions, ExternalTopics
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


    def send_to_other_system(
        self,
        target_topic: str,
        action: str,
        payload: dict,
        correlation_id: Optional[str] = None,
        timeout: float = 10.0,
    ) -> Optional[dict]:
        message = {
            "action": action,
            "sender": self.component_id,
            "payload": payload,
        }
        if correlation_id:
            message["correlation_id"] = correlation_id

        return self.bus.request(
            target_topic,
            message,
            timeout=timeout,
        )

    def publish_to_other_system(
        self,
        target_topic: str,
        action: str,
        payload: dict,
        correlation_id: Optional[str] = None,
    ) -> None:
        message = {
            "action": action,
            "sender": self.component_id,
            "payload": payload,
        }
        if correlation_id:
            message["correlation_id"] = correlation_id

        self.bus.publish(
            target_topic, 
            message
        )


    def _handle_mission_upload(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = payload.get("mission_id")
        drone_id = payload.get("drone_id")
        wpl = payload.get("wpl")

        self.publish_to_other_system(
            ExternalTopics.DRONE,
            "upload_mission",
            {
                "mission_id": mission_id,
                "mission": wpl,
            },
            correlation_id=correlation_id,
        )

        self.publish_to_other_system(
            ComponentTopics.GCS_MISSION_STORE,
            "store.update_mission",
            {
                "mission_id": mission_id,
                "fields": {
                    "assigned_drone": drone_id,
                    "status": MissionStatus.ASSIGNED,
                },
            },
            correlation_id=correlation_id,
        )

        self.publish_to_other_system(
            ComponentTopics.GCS_DRONE_STORE,
            DroneStoreActions.UPDATE_DRONE,
            {
                "drone_id": drone_id,
                "status": DroneStatus.RESERVED,
            },
            correlation_id=correlation_id,
        )

        return None

    def _handle_telemetry_save(self, message: Dict[str, Any]) -> None:
        correlation_id = message.get("correlation_id")
        payload = message.get("payload")

        self.publish_to_other_system(
            ComponentTopics.GCS_DRONE_STORE,
            DroneStoreActions.SAVE_TELEMETRY,
            payload,
            correlation_id=correlation_id,
        )

    def _handle_mission_start(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = payload.get("mission_id")
        drone_id = payload.get("drone_id")

        self.publish_to_other_system(
            ExternalTopics.DRONE,
            "mission.start",
            {},
            correlation_id=correlation_id,
        )
        
        self.publish_to_other_system(
            ComponentTopics.GCS_MISSION_STORE,
            "store.update_mission",
            {
                "mission_id": mission_id,
                "fields": {
                    "status": MissionStatus.RUNNING,
                },
            },
            correlation_id=correlation_id,
        )

        self.publish_to_other_system(
            ComponentTopics.GCS_DRONE_STORE,
            DroneStoreActions.UPDATE_DRONE,
            {
                "drone_id": drone_id,
                "status": DroneStatus.BUSY,
            },
            correlation_id=correlation_id,
        )

        return None