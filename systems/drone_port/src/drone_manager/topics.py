"""
Топики для DroneManager.
Взаимодействие с физическими дронами и координация с другими компонентами.
"""

class DroneManagerTopics:
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.BASE = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.drone_manager"
        
        # === Команды от дронов ===
        self.REQUEST_LANDING = f"{self.BASE}.request_landing"
        self.REQUEST_TAKEOFF = f"{self.BASE}.request_takeoff"
        self.SELF_DIAGNOSTICS = f"{self.BASE}.self_diagnostics"
        
        # === Исходящие команды дронам ===
        self.EVENTS_BASE = f"{self.BASE}.events"
        self.LANDING_ALLOWED = f"{self.EVENTS_BASE}.landing_allowed"
        self.TAKEOFF_ALLOWED = f"{self.EVENTS_BASE}.takeoff_allowed"
        
        # === Внутренние команды (от других компонентов) ===
        self.REGISTER_DRONE = f"{self.BASE}.register_drone"
        self.DELETE_DRONE = f"{self.BASE}.delete_drone"
        self.GET_CHARGING_DATA = f"{self.BASE}.get_charging_data"
        
        # === SITL Integration ===
        self.GET_SITL_DATA = f"{self.BASE}.get_sitl_data"
        self.UPDATE_SITL_POSITION = f"{self.BASE}.update_sitl_position"
        
        # === Для Эксплуатанта ===
        self.GET_AVAILABLE_DRONES = f"{self.BASE}.get_available_drones"