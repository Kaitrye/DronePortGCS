"""
Топики для DroneportOrchestrator.
Единственная точка входа от Эксплуатанта.
"""

class DroneportOrchestratorTopics:
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.BASE = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.orchestrator"
        
        # === Входящие команды (ТОЛЬКО от Эксплуатанта) ===
        self.FLEET_REPORT = f"{self.BASE}.fleet.report"
        self.HEALTH_CHECK = f"{self.BASE}.health_check"
        
        # === Исходящие события ===
        self.EVENTS_BASE = f"{self.BASE}.events"
        self.FLEET_REPORT_READY = f"{self.EVENTS_BASE}.fleet_report_ready"
        self.SITL_POSITIONS = f"{self.EVENTS_BASE}.sitl.positions"

    def get_reply_topic(self, request_id: str) -> str:
        return f"replies.{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.orchestrator.{request_id}"