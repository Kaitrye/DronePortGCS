# create_event_bus is deprecated, use create_system_bus instead.
from broker.src.bus_factory import create_system_bus

__all__ = ["create_system_bus"]
