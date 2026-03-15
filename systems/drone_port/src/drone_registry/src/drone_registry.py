"""
DroneRegistry — Facade для сбора данных со всех компонентов.
Знает о PortManager, ChargingManager, DiagnosticsManager, DroneManager.
"""
import datetime
from typing import Dict, Any, List, Optional
from shared.base_system import BaseSystem
from broker.system_bus import SystemBus
from src.state_store.src.state_store import StateStore
from src.drone_registry.topics import DroneRegistryTopics
from src.port_manager.topics import PortManagerTopics
from src.charging_manager.topics import ChargingManagerTopics

class DroneRegistry(BaseSystem):
    def __init__(
        self,
        system_id: str,
        name: str,
        bus: SystemBus,
        state_store: StateStore,
        health_port: Optional[int] = None,
    ):
        self.topics = DroneRegistryTopics(system_id)
        self.port_topics = PortManagerTopics(system_id)
        self.charging_topics = ChargingManagerTopics(system_id)
        self.state = state_store
        
        super().__init__(
            system_id=system_id,
            system_type="droneport",
            topic=self.topics.BASE,
            bus=bus,
            health_port=health_port,
        )
        self.name = name
        print(f"DroneRegistry '{name}' initialized (Facade pattern)")
        
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.register_handler(self.topics.GET_AGGREGATED_FLEET_STATUS, self._handle_get_aggregated_status)
        self.register_handler(self.topics.REGISTER_DRONE, self._handle_register_drone)
        self.register_handler(self.topics.DELETE_DRONE, self._handle_delete_drone)
        self.register_handler(self.topics.GET_DRONE, self._handle_get_drone)
        self.register_handler(self.topics.LIST_DRONES, self._handle_list_drones)
        self.register_handler(self.topics.UPDATE_DRONE_STATE, self._handle_update_drone_state)

    def _handle_get_aggregated_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Facade метод: собирает данные со ВСЕХ компонентов."""
        request_id = message.get("request_id")
        
        drones = self.state.list_drones()
        
        ports_response = self.bus.request(
            self.port_topics.GET_PORT_STATUS,
            {"request_id": request_id},
            timeout=5.0
        )
        ports = ports_response.get("payload", []) if ports_response else []
        
        charging_response = self.bus.request(
            self.charging_topics.GET_CHARGING_STATUS,
            {"request_id": request_id},
            timeout=5.0
        )
        charging = charging_response.get("payload", []) if charging_response else []
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "fleet": {
                "total": len(drones),
                "charging": sum(1 for d in drones if d.get("status") == "charging"),
                "ready": sum(1 for d in drones if d.get("status") == "landed"),
                "issues": sum(1 for d in drones if d.get("issues"))
            },
            "ports": {
                "total": len(ports),
                "occupied": sum(1 for p in ports if p.get("drone_id")),
                "maintenance": sum(1 for p in ports if p.get("status") == "maintenance")
            },
            "charging_status": charging,
            "alerts": [
                {"drone_id": d["drone_id"], "issue": d["issues"]}
                for d in drones if d.get("issues")
            ]
        }

    def _handle_register_drone(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Регистрация дрона в реестре"""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        drone_data = {
            "drone_id": drone_id,
            "battery_level": str(payload.get("battery_level", 0.0)),
            "port_id": payload.get("port_id", ""),
            "status": payload.get("status", "landed"),
            "last_update": datetime.utcnow().isoformat()
        }
        
        self.state.save_drone(drone_id, drone_data)
        
        self.bus.publish(
            self.topics.DRONE_REGISTERED,
            {"drone_id": drone_id, "timestamp": datetime.utcnow().isoformat()}
        )
        
        return {"status": "registered", "drone_id": drone_id}

    def _handle_delete_drone(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Удаление дрона из реестра"""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        self.state.delete_drone(drone_id)
        
        self.bus.publish(
            self.topics.DRONE_DELETED,
            {"drone_id": drone_id, "timestamp": datetime.utcnow().isoformat()}
        )
        
        return {"status": "deleted", "drone_id": drone_id}

    def _handle_get_drone(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение данных о дроне"""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        drone = self.state.get_drone(drone_id)
        if not drone:
            return {"status": "not_found", "drone_id": drone_id}
        
        bat = float(drone.get("battery_level", 100.0))
        drone["safety_target"] = "normal_operation"
        drone["issues"] = []
        
        if bat < 20.0:
            drone["safety_target"] = "low_battery_alert"
            drone["issues"].append("battery_critical")
        
        return {"status": "ok", "drone": drone}

    def _handle_list_drones(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Список всех дронов"""
        drones = self.state.list_drones()
        
        for d in drones:
            bat = float(d.get("battery_level", 100.0))
            d["safety_target"] = "normal_operation" if bat >= 20.0 else "low_battery_alert"
            d["issues"] = ["battery_critical"] if bat < 20.0 else []
        
        return {"status": "ok", "drones": drones}

    def _handle_update_drone_state(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление состояния дрона"""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        drone = self.state.get_drone(drone_id)
        if drone:
            drone.update({
                "issues": payload.get("issues", []),
                "health_data": payload.get("health_data", {}),
                "last_update": datetime.utcnow().isoformat()
            })
            self.state.save_drone(drone_id, drone)
            
            if payload.get("issues"):
                self.bus.publish(
                    self.topics.SAFETY_ALERT,
                    {"drone_id": drone_id, "issues": payload["issues"]}
                )
        
        return {"status": "updated", "drone_id": drone_id}