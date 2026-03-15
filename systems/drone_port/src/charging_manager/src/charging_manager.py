"""
ChargingManager — ТОЛЬКО логика зарядки дронов.
"""

import datetime
from typing import Dict, Any, Optional
from shared.base_system import BaseSystem
from broker.src.system_bus import SystemBus
from src.state_store.src.state_store import StateStore
from src.charging_manager.topics import ChargingManagerTopics
from src.drone_registry.topics import DroneRegistryTopics

class ChargingManager(BaseSystem):
    def __init__(
        self,
        system_id: str,
        name: str,
        bus: SystemBus,
        state_store: StateStore,
        health_port: Optional[int] = None,
    ):
        self.topics = ChargingManagerTopics(system_id)
        self.registry_topics = DroneRegistryTopics(system_id)
        self.state = state_store
        
        super().__init__(
            system_id=system_id,
            system_type="droneport",
            topic=self.topics.BASE,
            bus=bus,
            health_port=health_port,
        )
        self.name = name
        print(f"ChargingManager '{name}' initialized")
        
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.register_handler(self.topics.START_CHARGING, self._handle_start_charging)
        self.register_handler(self.topics.STOP_CHARGING, self._handle_stop_charging)
        self.register_handler(self.topics.CHARGE_TO_THRESHOLD, self._handle_charge_to_threshold)
        self.register_handler(self.topics.GET_CHARGING_STATUS, self._handle_get_charging_status)

    def _handle_start_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        drone = self.state.get_drone(drone_id)
        if not drone:
            return {"status": "failed", "reason": "Drone not found"}
        
        drone.update({
            "status": "charging",
            "charging_started": datetime.utcnow().isoformat()
        })
        self.state.save_drone(drone_id, drone)
        
        self.bus.publish(
            self.topics.CHARGING_STARTED,
            {"drone_id": drone_id, "timestamp": datetime.utcnow().isoformat()}
        )
        
        return {"status": "charging_started", "drone_id": drone_id}

    def _handle_stop_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        drone = self.state.get_drone(drone_id)
        if drone:
            drone.update({
                "status": "landed",
                "charging_completed": datetime.utcnow().isoformat()
            })
            self.state.save_drone(drone_id, drone)
        
        self.bus.publish(
            self.topics.CHARGING_COMPLETED,
            {"drone_id": drone_id, "timestamp": datetime.utcnow().isoformat()}
        )
        
        return {"status": "charging_stopped", "drone_id": drone_id}

    def _handle_charge_to_threshold(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        min_battery = float(payload.get("min_battery", 90.0))
        current_battery = float(payload.get("current_battery", 50.0))
        departure_time_sec = payload.get("departure_time_sec", 3600)
        
        if current_battery >= min_battery:
            return {
                "status": "charge.not_required",
                "drone_id": drone_id,
                "battery_level": current_battery
            }
        
        delta_bat = min_battery - current_battery
        required_energy_wh = delta_bat * 0.1
        max_power_w = 500.0
        charging_power_w = min(max_power_w, required_energy_wh * 3600 / departure_time_sec)
        
        drone = self.state.get_drone(drone_id)
        if drone:
            drone.update({
                "charging_power_w": str(charging_power_w),
                "target_battery": str(min_battery),
                "status": "charging"
            })
            self.state.save_drone(drone_id, drone)
        
        # Обновление данных в DroneRegistry
        self.bus.request(
            self.registry_topics.UPDATE_DRONE_STATE,
            {
                "payload": {
                    "drone_id": drone_id,
                    "battery_level": str(min_battery),
                    "charging_power_w": str(charging_power_w)
                }
            },
            timeout=5.0
        )
        
        return {
            "status": "charge.completed",
            "drone_id": drone_id,
            "charging_power_w": charging_power_w,
            "estimated_finish_sec": int(required_energy_wh * 3600 / charging_power_w) if charging_power_w > 0 else 0
        }

    def _handle_get_charging_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        drones = self.state.list_drones()
        charging_drones = [d for d in drones if d.get("status") == "charging"]
        
        return {
            "status": "ok",
            "payload": [
                {
                    "drone_id": d["drone_id"],
                    "battery_level": d.get("battery_level", 0),
                    "charging_power_w": d.get("charging_power_w", 0),
                    "target_battery": d.get("target_battery", 100)
                }
                for d in charging_drones
            ]
        }


# В конец файла charging_manager.py добавьте:

def main():
    import os
    import redis
    from broker.system_bus import SystemBus
    from state_store.src.state_store import StateStore
    
    system_id = os.getenv("SYSTEM_ID", "dp-001")
    component_id = os.getenv("COMPONENT_ID", "charging_manager")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    broker_host = os.getenv("BROKER_HOST", "localhost")
    broker_port = int(os.getenv("BROKER_PORT", 1883))
    health_port = int(os.getenv("HEALTH_PORT", 8084))
    
    redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    state_store = StateStore(redis_client)
    bus = SystemBus(component_id, host=broker_host, port=broker_port)
    
    manager = ChargingManager(
        system_id=system_id,
        name=component_id,
        bus=bus,
        state_store=state_store,
        health_port=health_port
    )
    
    manager.run()