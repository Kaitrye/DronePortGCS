"""
Топики для ChargingManager.
ТОЛЬКО логика зарядки.
"""

class ChargingManagerTopics:
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.BASE = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.charging_manager"
        
        # === Команды ===
        self.START_CHARGING = f"{self.BASE}.start_charging"
        self.STOP_CHARGING = f"{self.BASE}.stop_charging"
        self.CHARGE_TO_THRESHOLD = f"{self.BASE}.charge_to_threshold"
        self.GET_CHARGING_STATUS = f"{self.BASE}.get_status"
        
        # === События ===
        self.EVENTS_BASE = f"{self.BASE}.events"
        self.CHARGING_STARTED = f"{self.EVENTS_BASE}.charging_started"
        self.CHARGING_COMPLETED = f"{self.EVENTS_BASE}.charging_completed"
        self.CHARGING_PROGRESS = f"{self.EVENTS_BASE}.charging_progress"