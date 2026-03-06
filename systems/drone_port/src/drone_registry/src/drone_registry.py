"""
DroneRegistry — централизованный реестр дронов.
Возвращает список с safety_target и issues (для ОФ4).
"""

import datetime
from typing import Dict, Any, List, Optional
from src.state_store.src.state_store import StateStore


class DroneRegistry:
    def __init__(self, state_store: StateStore):
        self.state = state_store

    def list_all_drones(self) -> List[Dict[str, Any]]:
        drones = self.state.list_drones()
        result = []
        for d in drones:
            bat = float(d.get("battery_level", 100.0))
            safety_target = "normal_operation"
            issues = []

            if bat < 20.0:
                safety_target = "low_battery_alert"
                issues.append("battery_critical")

            result.append({
                "drone_id": d["drone_id"],
                "port_id": d.get("port_id", ""),
                "battery_level": bat,
                "status": d.get("status", "unknown"),
                "safety_target": safety_target,
                "issues": issues,
                "last_update": d.get("last_update")
            })
        return result
    
    def register_drone(self, drone_id: str, battery_level: float, port_id: str, specs: Dict = None) -> Dict[str, Any]:
        """Регистрирует дрон в реестре с базовыми параметрами."""
        drone_data = {
            "drone_id": drone_id,
            "battery_level": str(battery_level),
            "port_id": port_id,
            "status": "landed",
            "last_update": datetime.utcnow().isoformat()
        }
        if specs:
            drone_data.update(specs)
            
        self.state.save_drone(drone_id, drone_data)
        # Сохраняем мета-данные отдельно для валидации
        if specs:
            self.state.register_drone_meta(drone_id, specs)
            
        return {"status": "registered", "drone_id": drone_id}

    def get_drone(self, drone_id: str) -> Optional[Dict[str, Any]]:
        """Получает полные данные о дроне, включая расчет safety_target."""
        drone = self.state.get_drone(drone_id)
        if not drone:
            return None
            
        # Обогащаем данные логикой безопасности
        bat = float(drone.get("battery_level", 100.0))
        drone["safety_target"] = "normal_operation"
        drone["issues"] = []
        
        if bat < 20.0:
            drone["safety_target"] = "low_battery_alert"
            drone["issues"].append("battery_critical")
            
        return drone

    def run_post_landing_diagnostics(self, drone_id: str) -> Dict[str, Any]:
        """Запускает диагностику на основе данных из реестра."""
        drone = self.get_drone(drone_id)
        if not drone:
            return {"status": "diagnostics.failed", "error_code": "DRONE_NOT_FOUND"}
            
        if drone.get("issues"):
            return {
                "status": "diagnostics.failed",
                "drone_id": drone_id,
                "issues": drone["issues"]
            }
        return {"status": "diagnostics.ok", "drone_id": drone_id}