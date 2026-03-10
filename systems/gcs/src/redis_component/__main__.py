import os

from broker.bus_factory import create_system_bus
from systems.gcs.src.redis_component.src.redis_component import RedisComponent


def main():
    component_id = os.environ.get("COMPONENT_ID", "gcs_redis")
    health_port = int(os.environ.get("HEALTH_PORT", "9806"))

    bus = create_system_bus(client_id=component_id)
    component = RedisComponent(system_id=component_id, bus=bus, health_port=health_port)
    component.run_forever()


if __name__ == "__main__":
    main()
