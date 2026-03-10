import os

from broker.bus_factory import create_system_bus
from systems.gcs.src.mission_component.src.mission_component import MissionComponent


def main():
    component_id = os.environ.get("COMPONENT_ID", "gcs_mission")
    health_port = int(os.environ.get("HEALTH_PORT", "9800"))

    bus = create_system_bus(client_id=component_id)
    component = MissionComponent(system_id=component_id, bus=bus, health_port=health_port)
    component.run_forever()


if __name__ == "__main__":
    main()
