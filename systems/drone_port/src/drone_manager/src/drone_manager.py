"""
DroneManager — взаимодействие с физическими дронами.
"""
import datetime
from typing import Dict, Any
from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.drone_port.src.charging_manager.topics import ComponentTopics as ChargingTopics, ChargingManagerActions
from systems.drone_port.src.drone_manager.topics import ComponentTopics as DroneManagerTopics, DroneManagerActions
from systems.drone_port.src.port_manager.topics import ComponentTopics as PortTopics, PortManagerActions


class DroneManager(BaseComponent):
    """
    Передает запросы:
    - от дронов к PortManager (landing/takeoff)
    - от дронов к ChargingManager (charging)
    """
    
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
    ):
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=DroneManagerTopics.DRONE_MANAGER,
            bus=bus,
        )
        self.name = name

    def _register_handlers(self) -> None:
        self.register_handler(DroneManagerActions.REQUEST_LANDING, self._handle_landing)
        self.register_handler(DroneManagerActions.REQUEST_TAKEOFF, self._handle_takeoff)
        self.register_handler(DroneManagerActions.REQUEST_CHARGING, self._handle_charging)

    def _handle_landing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запрос на посадку от дрона.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        model = payload.get("model", "unknown")

        response = self.bus.request(
            PortTopics.PORT_MANAGER,
            {
                "action": PortManagerActions.REQUEST_LANDING_SLOT,
                "payload": {
                    "drone_id": drone_id
                },
                "sender": self.component_id,
            },
            timeout=3.0
        )

        if response and response.get("success"):
            self.bus.publish(
                DroneManagerTopics.DRONE_REGISTRY,
                {
                    "action": DroneRegistryActions.REGISTER_DRONE,
                    "payload": {
                        "drone_id": drone_id,
                        "model": model,
                        "port_id": response.get("port_id"),
                    },
                    "sender": self.component_id,
                }
            )

            port_id = response.get("port_id")
            return {
                "port_id": port_id,
                "from": self.component_id,
            }
        
        return {
            "error": "No free ports",
            "from": self.component_id
        }

    def _handle_takeoff(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запрос на взлет от дрона.
        """
        payload = message.get("payload")
        drone_id = payload.get("drone_id")
        port_response = self.bus.request(
            PortTopics.PORT_MANAGER,
            {
                "action": PortManagerActions.GET_PORT_STATUS,
                "payload": {},
            },
            timeout=3.0,
        )
        ports = (port_response or {}).get("ports", [])
        drone_port = next(
            (port for port in ports if port.get("drone_id") == drone_id),
            None,
        )

        response = self.bus.request(
            DroneRegistryTopics.DRONE_REGISTRY,
            {
                "action": DroneRegistryActions.GET_DRONE,
                "payload": {
                    "drone_id": drone_id
                },
                "sender": self.component_id,
            }
        )

        if response and response.get("success"):
            battery = response.get("battery")
            port_id = response.get("port_id")

            if battery > 80.0:
                port_response = self.bus.request(
                    PortTopics.PORT_MANAGER,
                    {
                        "action": PortManagerActions.FREE_SLOT,
                        "payload": {
                            "drone_id": drone_id,
                            "port_id": port_id,
                        },
                        "sender": self.component_id,
                    }
                )

                self.bus.publish(
                    ExternalTopics.SITL,
                    {
                        "action": SITLActions.STARTED_TAKEOFF,
                        "payload": {
                            "drone_id": drone_id,
                            "port_id": port_id,
                            "port_coordinates": {
                                "lat": port_response.get("lat"),
                                "lon": port_response.get("lon"),
                            },
                            "battery": battery,
                        },
                        "sender": self.component_id,
                    }
                )

                return {
                    "battery": battery,
                    "from": self.component_id,
                }

            return {
                "error": "Not enough battery for takeoff",
                "from": self.component_id
            }

        return {
            "error": "Failed to get drone information",
            "from": self.component_id
        }

    def _handle_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запрос на зарядку от дрона.        
        Дрон всегда запрашивает зарядку самостоятельно.
        """
        payload = message.get("payload")
        drone_id = payload.get("drone_id")
        battery = payload.get("battery")

        self.bus.publish(
            ChargingTopics.CHARGING_MANAGER,
            {
                "action": ChargingManagerActions.START_CHARGING,
                "payload": {
                    "drone_id": drone_id,
                    "battery": battery,
                }
            }
        )

        return None
