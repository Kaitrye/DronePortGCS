"""
Топики для PortManager.
Управление посадочными местами.
"""

class PortManagerTopics:
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.BASE = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.port_manager"
        
        # === Команды ===
        self.RESERVE_SLOT = f"{self.BASE}.reserve_slot"
        self.RELEASE_SLOT = f"{self.BASE}.release_slot"
        self.REQUEST_LANDING_SLOT = f"{self.BASE}.request_landing_slot"
        self.GET_PORT_STATUS = f"{self.BASE}.get_port_status"
        
        # === События ===
        self.EVENTS_BASE = f"{self.BASE}.events"
        self.SLOT_RESERVED = f"{self.EVENTS_BASE}.slot_reserved"
        self.SLOT_RELEASED = f"{self.EVENTS_BASE}.slot_released"
        self.SLOT_ASSIGNED = f"{self.EVENTS_BASE}.slot_assigned"