"""
PowerHealthManager — объединённый компонент для:
- зарядки до порога (`charge_to_threshold`)
- пост-посадочной диагностики (`run_post_landing_diagnostics`)
- автоматической зарядки после посадки (`auto_start_charging_if_needed`)
"""

from typing import Dict, Any
from src.state_store.src.state_store import StateStore


class PowerHealthManager:
    def __init__(self, state_store: StateStore):
        self.state = state_store

    def charge_to_threshold(
        self,
        drone_id: str,
        min_battery: float,
        current_battery: float,
        departure_time_sec: int = 3600
    ) -> Dict[str, Any]:
        if current_battery >= min_battery:
            return {
                "status": "charge.not_required",
                "drone_id": drone_id,
                "battery_level": current_battery
            }

        delta_bat = min_battery - current_battery
        required_energy_wh = delta_bat * 0.1  # условная ёмкость = 10 Wh
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

        return {
            "status": "charge.completed",
            "drone_id": drone_id,
            "charging_power_w": charging_power_w,
            "estimated_finish_sec": int(required_energy_wh * 3600 / charging_power_w) if charging_power_w > 0 else 0
        }

    def run_post_landing_diagnostics(self, drone_id: str) -> Dict[str, Any]:
        drone = self.state.get_drone(drone_id)
        if not drone:
            return {
                "status": "diagnostics.failed",
                "error_code": "INTERNAL_ERROR",
                "reason": "Drone not found"
            }

        issues = []
        bat = float(drone.get("battery_level", 100.0))
        if bat < 10.0:
            issues.append("battery_critical")

        # Можно расширить: температура, связь, GPS, etc.
        if issues:
            drone["issues"] = ",".join(issues)
            self.state.save_drone(drone_id, drone)
            return {
                "status": "diagnostics.failed",
                "drone_id": drone_id,
                "issues": issues
            }

        return {
            "status": "diagnostics.ok",
            "drone_id": drone_id
        }

    def auto_start_charging_if_needed(self, drone_id: str) -> Dict[str, Any]:
        drone = self.state.get_drone(drone_id)
        if not drone:
            return { "status": "charging.not_required" }

        bat = float(drone.get( "battery_level", 100.0))
        if bat < 80.0:
            drone[ "status"] = "auto_charging"
            self.state.save_drone(drone_id, drone)
            return { 
                "status": "charging.started",
                "drone_id": drone_id
            }

        return { "status": "charging.not_required", "drone_id": drone_id}
    
    def query_drone_self_diagnostics(self, drone_id: str) -> Dict[str, Any]:
        """
        Запрашивает данные самодиагностики у физического дрона.
        В реальной системе здесь будет вызов MAVLink/ArduPilot API.
        """
        # TODO: Интеграция с DroneTelemetryClient
        # client = DroneTelemetryClient(drone_id)
        # return client.get_health_report()
        
        # Заглушка для демонстрации логики:
        return {
            "motors": "ok",
            "gps_signal": "strong",
            "sensors": "calibrated",
            "internal_temp_c": 45
        }

    def run_post_landing_diagnostics(self, drone_id: str) -> Dict[str, Any]:
        """Расширенная диагностика: объединяет данные из StateStore и опрос дрона."""
        drone = self.state.get_drone(drone_id)
        if not drone:
            return {"status": "diagnostics.failed", "error_code": "DRONE_NOT_FOUND"}

        issues = []
        
        # 1. Проверка данных из хранилища (батаря)
        bat = float(drone.get("battery_level", 100.0))
        if bat < 10.0:
            issues.append("battery_critical")

        # 2. НОВАЯ ЛОГИКА: Опрос систем самодиагностики дрона
        try:
            remote_health = self.query_drone_self_diagnostics(drone_id)
            if remote_health.get("motors") != "ok":
                issues.append("motor_fault_detected")
            if remote_health.get("internal_temp_c", 0) > 80:
                issues.append("overheating")
        except Exception as e:
            # Если дрон не отвечает на запрос диагностики
            issues.append("telemetry_link_lost")

        # Сохранение результатов
        if issues:
            drone["issues"] = ", ".join(issues) # Или список, в зависимости от схемы
            self.state.save_drone(drone_id, drone)
            return {"status": "diagnostics.failed", "drone_id": drone_id, "issues": issues}

        return {"status": "diagnostics.ok", "drone_id": drone_id}