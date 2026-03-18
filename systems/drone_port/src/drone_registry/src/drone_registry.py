"""
DroneRegistry — реестр дронов и фасад для агрегации данных.
"""
import datetime
from typing import Dict, Any, List
from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.drone_port.src.drone_registry.topics import DroneRegistryTopics


class DroneRegistry(BaseComponent):
    """
    Общается с:
    - Orchestrator (получает команды)
    - ChargingManager (статус зарядки)
    - DroneManager (доступные дроны)
    """
    
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
    ):
        self.topics = DroneRegistryTopics(component_id)
        
        self._registered_drones: Dict[str, Dict[str, Any]] = {
            "DR-001": {
                "drone_id": "DR-001",
                "model": "QuadroX",
                "owner": "AlphaFlight",
                "registered_at": "2026-01-01T00:00:00Z"
            },
            "DR-002": {
                "drone_id": "DR-002",
                "model": "HexaLift",
                "owner": "BetaOps", 
                "registered_at": "2026-01-01T00:00:00Z"
            },
            "DR-003": {
                "drone_id": "DR-003",
                "model": "OctoPlus",
                "owner": "GammaCorp",
                "registered_at": "2026-01-01T00:00:00Z"
            },
        }
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic,
            bus=bus,
        )
        self.name = name
        print(f"DroneRegistry '{name}' initialized")

    def _register_handlers(self) -> None:
        self.register_handler("register_drone", self._handle_register)
        self.register_handler("list_drones", self._handle_list)
        self.register_handler("get_aggregated_status", self._handle_get_aggregated)
        self.register_handler("start_charging", self._handle_start_charging)

    def _handle_register(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Регистрация нового дрона.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {
                "status": "error",
                "reason": "Missing drone_id"
            }
        
        self._registered_drones[drone_id] = {
            "drone_id": drone_id,
            "model": payload.get("model", "unknown"),
            "owner": payload.get("owner", "unknown"),
            "registered_at": datetime.datetime.utcnow().isoformat(),
        }
        
        self.bus.publish(
            self.topics.DRONE_REGISTERED,
            {
                "event": "drone_registered",
                "drone_id": drone_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )
        
        return {
            "status": "success",
            "drone_id": drone_id
        }

    def _handle_list(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Список всех зарегистрированных дронов.
        """
        return {
            "status": "success",
            "count": len(self._registered_drones),
            "drones": list(self._registered_drones.values())
        }

    def _handle_get_aggregated(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Агрегированный статус системы.
        
        Опрашивает:
        - DroneManager (доступные дроны)
        - ChargingManager (статус зарядки)
        """
        request_id = message.get("request_id")
        
        # 1. Запрашиваем доступные дроны у DroneManager
        drones_response = self.bus.request(
            "v1.droneport.dp-001.drone_manager.get_available_drones",
            {"request_id": request_id, "payload": {}},
            timeout=3.0
        )
        
        # 2. Запрашиваем статус зарядки у ChargingManager
        charging_response = self.bus.request(
            "v1.droneport.dp-001.charging_manager.get_charging_status",
            {"request_id": request_id, "payload": {}},
            timeout=3.0
        )
        
        # Парсим ответы
        available_drones = []
        if drones_response and drones_response.get("status") == "success":
            available_drones = drones_response.get("payload", {}).get("drones", [])
        
        charging_sessions = []
        if charging_response and charging_response.get("status") == "success":
            charging_sessions = charging_response.get("active_sessions", [])
        
        # Формируем алерты (только по своим данным)
        alerts = []
        
        # Алерт: низкий заряд у доступных дронов
        for drone in available_drones:
            if drone.get("battery", 100) < 20:
                alerts.append({
                    "type": "LOW_BATTERY",
                    "drone_id": drone["drone_id"],
                    "battery": drone["battery"],
                    "message": f"Drone {drone['drone_id']} has low battery"
                })
        
        # Алерт: много дронов заряжается (может быть проблема)
        if len(charging_sessions) > 3:
            alerts.append({
                "type": "MANY_CHARGING",
                "count": len(charging_sessions),
                "message": f"{len(charging_sessions)} drones are charging"
            })
        
        return {
            "status": "success",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "payload": {
                "registered_count": len(self._registered_drones),
                "available_drones": available_drones,
                "charging_sessions": charging_sessions,
                "alerts": alerts
            }
        }

    def _handle_start_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запуск зарядки дрона.
        
        Перенаправляет запрос в ChargingManager.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {
                "status": "error",
                "reason": "Missing drone_id"
            }
        
        # Проверяем, что дрон зарегистрирован
        if drone_id not in self._registered_drones:
            return {
                "status": "error",
                "reason": f"Drone {drone_id} not registered"
            }
        
        # Отправляем команду в ChargingManager
        response = self.bus.request(
            "v1.droneport.dp-001.charging_manager.start_charging",
            {
                "request_id": message.get("request_id"),
                "payload": {
                    "drone_id": drone_id,
                    "target_battery": payload.get("target_battery", 100.0)
                }
            },
            timeout=5.0
        )
        
        if not response:
            return {
                "status": "error",
                "reason": "ChargingManager not responding"
            }
        
        return response