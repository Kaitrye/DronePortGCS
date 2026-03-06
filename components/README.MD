<<<<<<< HEAD
# Components

Компоненты - модули дрона, взаимодействующие через EventBus.

Шаблон: `dummy_component/`
=======
# Компоненты

Шаблон: `components/dummy_component/`

## Создать свой компонент

1. Скопировать `dummy_component` → `components/my_component/`
2. В `src/my_component.py`: наследоваться от `BaseComponent`, реализовать `_register_handlers()`
3. `__main__.py` — точка входа (standalone без брокера)
4. `docker/Dockerfile` — `CMD ["python", "-m", "components.my_component"]`
5. `Makefile`: `docker-build`, `docker-up`, `unit-test`
>>>>>>> origin/draft_GCS

## Структура

```
components/my_component/
├── src/
<<<<<<< HEAD
│   ├── __init__.py
│   └── my_component.py
└── tests/
    └── test_my_component.py
```

## Класс компонента

```python
from broker import EventBus
from shared.event import Event

class MyComponent:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe("my_component", self._handle_event)

    def _handle_event(self, event: Event):
        if event.operation == "do_action":
            response = Event(
                source="my_component",
                destination=event.source,
                operation="action_result",
                parameters={"result": "ok"}
            )
            self.event_bus.publish(response, event.source)
```

## EventBus API

```python
self.event_bus.subscribe("my_component", self._handle_event)
self.event_bus.publish(event, destination)
```
=======
│   └── my_component.py    # Класс от BaseComponent
├── __main__.py            # Запуск standalone
├── docker/Dockerfile
├── tests/
└── Makefile
```

## Класс

```python
from sdk.base_component import BaseComponent

class MyComponent(BaseComponent):
    def __init__(self, component_id: str, name: str, bus: SystemBus, topic: str = "components.my_component"):
        super().__init__(component_id=component_id, component_type="my_component", topic=topic, bus=bus)

    def _register_handlers(self):
        self.register_handler("action_name", self._handle_action)
```

## В составе системы

Компонент копируется целиком в `systems/my_system/src/my_component_a/`. Добавляются `topics.py`, `.env` (COMPONENT_ID, BROKER_USER, BROKER_PASSWORD), `__main__.py` с подключением к брокеру.
>>>>>>> origin/draft_GCS
