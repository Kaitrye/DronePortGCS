import os

from broker.bus_factory import create_system_bus
from systems.gcs.src.robot_component.src.robot_component import RobotComponent


def main():
    component_id = os.environ.get("COMPONENT_ID", "gcs_robot")
    health_port = int(os.environ.get("HEALTH_PORT", "9803"))

    bus = create_system_bus(client_id=component_id)
    component = RobotComponent(system_id=component_id, bus=bus, health_port=health_port)
    component.run_forever()


if __name__ == "__main__":
    main()
