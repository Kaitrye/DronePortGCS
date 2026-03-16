"""
PortManager — управление посадочными площадками.
"""
from typing import Dict, Any, List, Optional
from sdk.base_component import BaseComponent
from broker.mqtt.mqtt_system_bus import MQTTSystemBus
from systems.drone_port.src.state_store.src.state_store import StateStore
from systems.drone_port.src.port_manager.topics import PortManagerTopics


class PortManager(BaseComponent):
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: MQTTSystemBus,
        state_store: StateStore,
    ):
        self.topics = PortManagerTopics(component_id)
        self.state = state_store
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic,
            bus=bus,
        )
        self.name = name
        print(f"PortManager '{name}' initialized")

    def _register_handlers(self) -> None:
        """Регистрация обработчиков по action (строка), не по топику!"""
        self.register_handler("reserve_slot", self._handle_reserve_slot)
        self.register_handler("release_slot", self._handle_release_slot)
        self.register_handler("request_landing_slot", self._handle_request_landing_slot)
        self.register_handler("get_port_status", self._handle_get_port_status)

    def _handle_reserve_slot(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        port_id = payload.get("port_id")
        mission_window = payload.get("mission_window", {})
        
        if self.state.is_port_occupied(port_id):
            return {
                "status": "rejected",
                "error_code": "PORT_RESOURCE_BUSY",
                "reason": f"Port {port_id} is occupied",
                "retryable": True
            }
        
        self.state.save_port(port_id, {
            "port_id": port_id,
            "drone_id": drone_id,
            "status": "reserved",
            "mission_window_start": mission_window.get("start"),
            "mission_window_end": mission_window.get("end")
        })
        
        return {"status": "reserved", "port_id": port_id, "drone_id": drone_id}

    def _handle_release_slot(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        drone = self.state.get_drone(drone_id)
        if not drone:
            return {"status": "failed", "reason": "Drone not found"}
        
        port_id = drone.get("port_id")
        if port_id:
            self.state.save_port(port_id, {
                "port_id": port_id,
                "drone_id": "",
                "status": "free"
            })
            self.state.delete_drone(drone_id)
        
        return {"status": "release_ack", "drone_id": drone_id}

    def _handle_request_landing_slot(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        preferred_ports = payload.get("preferred_ports", ["P-01", "P-02", "P-03", "P-04"])
        
        for pid in preferred_ports:
            if not self.state.is_port_occupied(pid):
                return {
                    "status": "slot_assigned",
                    "port_id": pid,
                    "drone_id": drone_id,
                    "corridor": self._generate_landing_corridor(pid)
                }
        
        return {
            "status": "denied",
            "error_code": "PORT_RESOURCE_BUSY",
            "reason": "No available slots",
            "retryable": True
        }

    def _handle_get_port_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        ports = self.state.get_all_ports_status()
        return {"status": "ok", "payload": ports}

    def _generate_landing_corridor(self, port_id: str) -> Dict[str, Any]:
        return {
            "entry_point": f"{port_id}-ENTRY",
            "altitude_m": 50,
            "approach_vector": "NORTH"
        }