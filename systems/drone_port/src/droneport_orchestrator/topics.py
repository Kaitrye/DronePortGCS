"""
Топики и действия для Droneport Orchestrator.
"""

class SystemTopics:
    """Системные топики для межсервисного взаимодействия."""
    DRONEPORT = "droneport.commands"
    DRONEPORT_EVENTS = "droneport.events"
    OPERATOR_REPORTS = "operator.reports"
    HEALTH_CHECKS = "system.health"


class DroneportActions:
    """Действия (команды) для дронопорта."""
    RESERVE_SLOTS = "reserve_slots"
    PREFLIGHT_CHECK = "preflight_check"
    CHARGE_TO_THRESHOLD = "charge_to_threshold"
    RELEASE_FOR_TAKEOFF = "release_for_takeoff"
    REQUEST_LANDING_SLOT = "request_landing_slot"
    DOCK = "dock"
    EMERGENCY_RECEIVE = "emergency_receive"
    HEALTH_CHECK = "health_check"
    OPERATOR_REPORT_REQUEST = "operator_report_request"