"""
Действия для компонента PortManager.
Используются DroneportSystem для маршрутизации команд.
"""

class PortManagerActions:
    RESERVE_SLOT = "reserve_slot"
    REQUEST_LANDING_SLOT = "request_landing_slot"
    RELEASE_FOR_TAKEOFF = "release_for_takeoff"