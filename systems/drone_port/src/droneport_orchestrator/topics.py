"""
Топики для DroneportOrchestrator.
"""
from enum import Enum


class DroneportOrchestratorTopics:
    """Топики компонента оркестрации дронопорта (точка входа от Эксплуатанта)."""
    
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "orchestrator"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Входящие команды (ТОЛЬКО от Эксплуатанта) ===
        self.FLEET_REPORT = f"{self.base_topic}.fleet.report"
        self.HEALTH_CHECK = f"{self.base_topic}.health_check"
        
        # === Исходящие события ===
        self.FLEET_REPORT_READY = f"{self.base_topic}.events.fleet_report_ready"
        self.SITL_POSITIONS = f"{self.base_topic}.events.sitl.positions"
        
        # === Actions для BaseComponent ===
        self.ACTIONS = {
            "fleet_report": self.FLEET_REPORT,
            "health_check": self.HEALTH_CHECK,
        }
    
    def get_reply_topic(self, request_id: str) -> str:
        """Получить топик для ответа."""
        return f"replies.{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}.{request_id}"
    
    def get_topic_for_action(self, action: str) -> str:
        """Получить топик для действия."""
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")