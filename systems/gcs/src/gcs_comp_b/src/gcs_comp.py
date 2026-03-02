from typing import Dict, Any

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus


class DummyComponent(BaseComponent):

    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
        topic: str = "components.gcs_comp_b",
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
