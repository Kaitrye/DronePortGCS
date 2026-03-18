"""
Топики для ChargingManager.
"""
class ChargingManagerTopics:    
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "charging_manager"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Команды (входящие) 
        self.START_CHARGING = f"{self.base_topic}.start_charging"
        
        # === События (исходящие) ===
        self.CHARGING_STARTED = f"{self.base_topic}.events.charging_started"
        self.CHARGING_COMPLETED = f"{self.base_topic}.events.charging_completed"
        
        # === Actions для BaseComponent ===
        self.ACTIONS = {
            "start_charging": self.START_CHARGING,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")