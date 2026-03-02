from typing import Dict, Any

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus

from systems.drone_port.src.dp_comp_a.topics import (
    ComponentTopics,
    DummyComponentActions,
)


class DummyComponent(BaseComponent):

    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
        topic: str = "components.dp_comp_a",
    ):
        self.name = name
        self._state = {"counter": 0}
        super().__init__(
            component_id=component_id,
            component_type="dummy_component",
            topic=topic,
            bus=bus,
        )
        print(f"DummyComponent '{name}' initialized")

    
