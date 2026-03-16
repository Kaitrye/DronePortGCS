"""
Топики для ChargingManager.
"""

class ChargingManagerTopics:
    """Топики компонента управления зарядкой."""
    
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "charging_manager"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Команды (входящие) ===
        self.START_CHARGING = f"{self.base_topic}.start_charging"
        self.STOP_CHARGING = f"{self.base_topic}.stop_charging"
        self.CHARGE_TO_THRESHOLD = f"{self.base_topic}.charge_to_threshold"
        self.GET_CHARGING_STATUS = f"{self.base_topic}.get_charging_status"
        
        # === События (исходящие) ===
        self.CHARGING_STARTED = f"{self.base_topic}.events.charging_started"
        self.CHARGING_COMPLETED = f"{self.base_topic}.events.charging_completed"
        self.CHARGING_FAILED = f"{self.base_topic}.events.charging_failed"
        
        # === Actions для BaseComponent ===
        self.ACTIONS = {
            "start_charging": self.START_CHARGING,
            "stop_charging": self.STOP_CHARGING,
            "charge_to_threshold": self.CHARGE_TO_THRESHOLD,
            "get_charging_status": self.GET_CHARGING_STATUS,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        """Получить топик для действия."""
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")