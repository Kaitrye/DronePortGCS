"""
Действия для компонента PowerHealthManager.
Соответствуют контракту из DronePort.md.
"""

class PowerHealthManagerActions:
    CHARGE_TO_THRESHOLD = "charge_to_threshold"
    RUN_POST_LANDING_DIAGNOSTICS = "run_post_landing_diagnostics"
    AUTO_START_CHARGING_IF_NEEDED = "auto_start_charging_if_needed"