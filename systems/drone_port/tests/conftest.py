from __future__ import annotations

from fnmatch import fnmatch
from types import SimpleNamespace
from unittest.mock import MagicMock
import sys
import types

import pytest

# Stub для flask (если нужно)
flask_stub = types.ModuleType("flask")
flask_stub.Flask = type("Flask", (), {})
flask_stub.jsonify = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
sys.modules.setdefault("flask", flask_stub)

# Stub для redis
redis_stub = types.ModuleType("redis")
redis_stub.Redis = type("Redis", (), {})
sys.modules.setdefault("redis", redis_stub)

# Импорты для monkeypatch (новые компоненты)
from systems.drone_port.src.charging_manager.src import charging_manager as charging_manager_module
from systems.drone_port.src.landing_manager.src import landing_manager as landing_manager_module
from systems.drone_port.src.takeoff_manager.src import takeoff_manager as takeoff_manager_module
from systems.drone_port.src.drone_registry.src import drone_registry as drone_registry_module
from systems.drone_port.src.port_manager.src import port_manager as port_manager_module
from systems.drone_port.src.gateway.src import gateway as gateway_module


class FakeRedis:
    """Фейковое Redis хранилище для тестов."""
    
    def __init__(self):
        self.data = {}

    def exists(self, key):
        return key in self.data

    def hset(self, key, mapping):
        entry = self.data.setdefault(key, {})
        entry.update(mapping)
        return 1

    def hgetall(self, key):
        return dict(self.data.get(key, {}))

    def hget(self, key, field):
        entry = self.data.get(key, {})
        return entry.get(field)

    def keys(self, pattern):
        return [key for key in self.data if fnmatch(key, pattern)]

    def delete(self, key):
        self.data.pop(key, None)
        return 1

    def flushall(self):
        self.data.clear()
        return True


class InMemoryBus:
    """In-memory брокер для интеграционных тестов."""
    
    def __init__(self):
        self.components = {}
        self.requests = []
        self.publishes = []

    def register(self, component):
        self.components[component.topic] = component

    def request(self, topic, message, timeout=None):
        self.requests.append((topic, message, timeout))
        component = self.components.get(topic)
        if component is None:
            return None
        handler = component._handlers.get(message.get("action"))
        if handler is None:
            return None
        return handler(message)

    def publish(self, topic, message):
        self.publishes.append((topic, message))
        component = self.components.get(topic)
        if component is None:
            return True
        handler = component._handlers.get(message.get("action"))
        if handler is not None:
            handler(message)
        return True

    def respond(self, *_args, **_kwargs):
        return True

    def start(self):
        return None

    def stop(self):
        return None

    def subscribe(self, *_args, **_kwargs):
        return None

    def unsubscribe(self, *_args, **_kwargs):
        return None


@pytest.fixture
def mock_bus():
    """Мок для шины сообщений."""
    bus = MagicMock()
    bus.request.return_value = None
    bus.publish.return_value = True
    bus.respond.return_value = True
    return bus


@pytest.fixture
def fake_redis():
    """Фейковое Redis хранилище."""
    return FakeRedis()


@pytest.fixture
def patch_droneport_redis(monkeypatch, fake_redis):
    """Подмена Redis на фейковое для всех компонентов."""
    monkeypatch.setattr(drone_registry_module.redis, "Redis", lambda **_kwargs: fake_redis)
    return fake_redis


@pytest.fixture
def patch_external_topics(monkeypatch):
    """Подмена внешних топиков для тестов."""
    monkeypatch.setattr(
        gateway_module,
        "ExternalTopics",
        SimpleNamespace(SITL_HOME="sitl.home"),
        raising=False,
    )


@pytest.fixture
def immediate_thread(monkeypatch):
    """Запускаем потоки синхронно для тестов ChargingManager."""
    
    class ImmediateThread:
        def __init__(self, target, args=(), daemon=None):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(charging_manager_module.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(charging_manager_module.time, "sleep", lambda *_args, **_kwargs: None)


@pytest.fixture
def integration_bus():
    """In-memory брокер для интеграционных тестов."""
    return InMemoryBus()


# ========== Фикстуры для компонентов ==========

@pytest.fixture
def landing_manager_with_bus(mock_bus):
    """LandingManager с мок-шиной."""
    from systems.drone_port.src.landing_manager.src.landing_manager import LandingManager
    return LandingManager(component_id="landing_manager", name="LandingManager", bus=mock_bus)


@pytest.fixture
def takeoff_manager_with_bus(mock_bus):
    """TakeoffManager с мок-шиной."""
    from systems.drone_port.src.takeoff_manager.src.takeoff_manager import TakeoffManager
    return TakeoffManager(component_id="takeoff_manager", name="TakeoffManager", bus=mock_bus)


@pytest.fixture
def port_manager_with_bus(mock_bus):
    """PortManager с мок-шиной."""
    from systems.drone_port.src.port_manager.src.port_manager import PortManager
    return PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)


@pytest.fixture
def drone_registry_with_redis(mock_bus, patch_droneport_redis):
    """DroneRegistry с фейковым Redis."""
    from systems.drone_port.src.drone_registry.src.drone_registry import DroneRegistry
    return DroneRegistry(
        component_id="drone_registry",
        name="DroneRegistry",
        bus=mock_bus,
        redis_host="localhost",
        redis_port=6379,
    )


@pytest.fixture
def charging_manager_with_bus(mock_bus):
    """ChargingManager с мок-шиной."""
    from systems.drone_port.src.charging_manager.src.charging_manager import ChargingManager
    return ChargingManager(component_id="charging_manager", name="ChargingManager", bus=mock_bus)


@pytest.fixture
def gateway_with_bus(mock_bus):
    """Gateway с мок-шиной."""
    from systems.drone_port.src.gateway.src.gateway import DronePortGateway
    return DronePortGateway(system_id="drone_port", bus=mock_bus, health_port=None)