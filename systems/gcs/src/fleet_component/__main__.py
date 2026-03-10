import os

from broker.bus_factory import create_system_bus
from systems.gcs.src.fleet_component.src.fleet_component import FleetComponent


def main():
    component_id = os.environ.get("COMPONENT_ID", "gcs_fleet")
    health_port = int(os.environ.get("HEALTH_PORT", "9802"))

    bus = create_system_bus(client_id=component_id)
    component = FleetComponent(system_id=component_id, bus=bus, health_port=health_port)
    component.run_forever()


if __name__ == "__main__":
    main()
