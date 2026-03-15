"""
DroneManager — взаимодействие с физическими дронами.
Запросы самодиагностики + координация с портами.
"""
import datetime
from typing import Dict, Any, Optional, List
from shared.base_system import BaseSystem
from broker.system_bus import SystemBus
from src.drone_manager.topics import DroneManagerTopics
from src.drone_registry.topics import DroneRegistryTopics
from src.port_manager.topics import PortManagerTopics
from src.charging_manager.topics import ChargingManagerTopics

class DroneManager(BaseSystem):
    def __init__(
        self,
        system_id: str,
        name: str,
        bus: SystemBus,
        health_port: Optional[int] = None,
    ):
        self.topics = DroneManagerTopics(system_id)
        self.registry_topics = DroneRegistryTopics(system_id)
        self.port_topics = PortManagerTopics(system_id)
        self.charging_topics = ChargingManagerTopics(system_id)
        
        super().__init__(
            system_id=system_id,
            system_type="droneport",
            topic=self.topics.BASE,
            bus=bus,
            health_port=health_port,
        )
        self.name = name
        print(f"DroneManager '{name}' initialized")
        
        # Хранилище позиций дронов для SITL
        self._drone_positions = {}
        
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Регистрация обработчиков команд от дронов"""
        self.register_handler(
            self.topics.REQUEST_LANDING,
            self._handle_request_landing
        )
        self.register_handler(
            self.topics.REQUEST_TAKEOFF,
            self._handle_request_takeoff
        )
        self.register_handler(
            self.topics.SELF_DIAGNOSTICS,
            self._handle_self_diagnostics
        )
        self.register_handler(
            self.topics.REGISTER_DRONE,
            self._handle_register_drone
        )
        self.register_handler(
            self.topics.DELETE_DRONE,
            self._handle_delete_drone
        )
        # SITL handlers
        self.register_handler(
            self.topics.GET_SITL_DATA,
            self._handle_get_sitl_data
        )
        self.register_handler(
            self.topics.UPDATE_SITL_POSITION,
            self._handle_update_sitl_position
        )
        # Эксплуатант handler
        self.register_handler(
            self.topics.GET_AVAILABLE_DRONES,
            self._handle_get_available_drones
        )

    def _handle_get_sitl_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Возвращает данные о дронах для SITL симулятора.
        Формат соответствует архитектуре SITL-module.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")  # Если None - вернуть все дроны
        
        if drone_id:
            # Данные для конкретного дрона
            position = self._drone_positions.get(drone_id, {})
            return {
                "status": "ok",
                "drone_id": drone_id,
                "timestamp": datetime.utcnow().isoformat(),
                "position": {
                    "lat": position.get("lat", 0.0),
                    "lon": position.get("lon", 0.0),
                    "alt": position.get("alt", 0.0),
                    "heading": position.get("heading", 0.0)
                },
                "velocity": {
                    "vx": position.get("vx", 0.0),
                    "vy": position.get("vy", 0.0),
                    "vz": position.get("vz", 0.0)
                },
                "battery": position.get("battery", 100.0),
                "mode": position.get("mode", "STANDBY"),
                "armed": position.get("armed", False)
            }
        else:
            # Данные для всех дронов
            drones_data = []
            for did, pos in self._drone_positions.items():
                drones_data.append({
                    "drone_id": did,
                    "position": {
                        "lat": pos.get("lat", 0.0),
                        "lon": pos.get("lon", 0.0),
                        "alt": pos.get("alt", 0.0),
                        "heading": pos.get("heading", 0.0)
                    },
                    "velocity": {
                        "vx": pos.get("vx", 0.0),
                        "vy": pos.get("vy", 0.0),
                        "vz": pos.get("vz", 0.0)
                    },
                    "battery": pos.get("battery", 100.0),
                    "mode": pos.get("mode", "STANDBY"),
                    "armed": pos.get("armed", False)
                })
            
            return {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "drones": drones_data,
                "total": len(drones_data)
            }

    def _handle_update_sitl_position(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновляет позицию дрона для SITL.
        Вызывается при получении телеметрии от дрона.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {"status": "failed", "error_code": "INVALID_PAYLOAD"}
        
        # Обновление позиции
        self._drone_positions[drone_id] = {
            "lat": payload.get("lat", 0.0),
            "lon": payload.get("lon", 0.0),
            "alt": payload.get("alt", 0.0),
            "heading": payload.get("heading", 0.0),
            "vx": payload.get("vx", 0.0),
            "vy": payload.get("vy", 0.0),
            "vz": payload.get("vz", 0.0),
            "battery": payload.get("battery", 100.0),
            "mode": payload.get("mode", "STANDBY"),
            "armed": payload.get("armed", False),
            "last_update": datetime.utcnow().isoformat()
        }
        
        return {
            "status": "position_updated",
            "drone_id": drone_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _handle_get_available_drones(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Возвращает список доступных дронов с их локацией для Эксплуатанта.
        """
        # Запрос данных из DroneRegistry
        response = self.bus.request(
            self.registry_topics.LIST_DRONES,
            {"payload": {}},
            timeout=5.0
        )
        
        if not response or response.get("status") != "ok":
            return {
                "status": "failed",
                "error_code": "REGISTRY_UNAVAILABLE",
                "drones": []
            }
        
        drones = response.get("drones", [])
        available_drones = []
        
        for drone in drones:
            # Фильтруем только доступные дроны (не в maintenance, не с критическими issues)
            if drone.get("status") in ["landed", "ready", "charging"]:
                issues = drone.get("issues", [])
                if "battery_critical" not in issues and "motor_fault" not in issues:
                    # Получаем позицию из SITL данных
                    position = self._drone_positions.get(drone["drone_id"], {})
                    
                    available_drones.append({
                        "drone_id": drone["drone_id"],
                        "status": drone.get("status"),
                        "battery_level": float(drone.get("battery_level", 0)),
                        "location": {
                            "lat": position.get("lat", 0.0),
                            "lon": position.get("lon", 0.0),
                            "alt": position.get("alt", 0.0)
                        },
                        "port_id": drone.get("port_id", ""),
                        "safety_target": drone.get("safety_target", "normal_operation"),
                        "last_update": position.get("last_update", drone.get("last_update"))
                    })
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "drones": available_drones,
            "total": len(available_drones)
        }

    # ... остальные методы (_handle_request_landing, _handle_request_takeoff, и т.д.)