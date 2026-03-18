"""
Топики для DroneportOrchestrator.
"""
class DroneportOrchestratorTopics:
    """Топики оркестратора - точка входа для Эксплуатанта."""
    
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "orchestrator"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Команды от Эксплуатанта ===
        self.FLEET_REPORT = f"{self.base_topic}.fleet_report"
        self.START_CHARGING = f"{self.base_topic}.start_charging"  # добавили
        
        # === Actions ===
        self.ACTIONS = {
            "fleet_report": self.FLEET_REPORT,
            "start_charging": self.START_CHARGING,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")