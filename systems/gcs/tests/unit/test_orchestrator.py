from types import SimpleNamespace

import pytest

from systems.gcs.src.orchestrator.src import orchestrator as orchestrator_module
from systems.gcs.src.orchestrator.src.orchestrator import OrchestratorComponent
from systems.gcs.src.orchestrator.topics import ComponentTopics, OrchestratorActions


@pytest.fixture
def component(mock_bus):
    return OrchestratorComponent(component_id="orchestrator", bus=mock_bus)

def test_handle_task_submit_returns_route_when_planner_succeeds(component, monkeypatch):
    monkeypatch.setattr(orchestrator_module, "uuid4", lambda: SimpleNamespace(hex="abcdef1234567890"))
    component.send_to_other_system = lambda *args, **kwargs: {
        "success": True,
        "payload": {
            "waypoints": [1, 2, 3, 4],
        },
    }

    result = component._handle_task_submit({"payload": {"type": "delivery"}, "correlation_id": "corr-10"})

    assert result == {
        "from": "orchestrator",
        "mission_id": "m-abcdef123456",
        "waypoints": [1, 2, 3, 4],
    }


def test_handle_task_submit_returns_error_when_planner_fails(component):
    component.send_to_other_system = lambda *args, **kwargs: {"success": False}

    result = component._handle_task_submit({"payload": {"type": "delivery"}, "correlation_id": "corr-11"})

    assert result == {"from": "orchestrator", "error": "failed to build route"}


def test_handle_task_submit_returns_error_for_short_route(component):
    component.send_to_other_system = lambda *args, **kwargs: {
        "success": True,
        "payload": {"waypoints": [1, 2, 3]},
    }

    result = component._handle_task_submit({"payload": {"type": "delivery"}, "correlation_id": "corr-12"})

    assert result == {"from": "orchestrator", "error": "failed to build route"}


def test_handle_task_assign_publishes_upload_when_converter_returns_wpl(component):
    calls = []
    component.send_to_other_system = lambda *args, **kwargs: {
        "success": True,
        "payload": {"mission": {"wpl": "QGC WPL 110"}},
    }
    component.publish_to_other_system = lambda *args, **kwargs: calls.append((args, kwargs))

    component._handle_task_assign(
        {
            "payload": {"mission_id": "m-assign", "drone_id": "dr-7"},
            "correlation_id": "corr-12",
        }
    )

    assert calls == [
        (
            (
                ComponentTopics.GCS_DRONE_MANAGER,
                "mission.upload",
                {"mission_id": "m-assign", "drone_id": "dr-7", "wpl": "QGC WPL 110"},
            ),
            {"correlation_id": "corr-12"},
        )
    ]


def test_handle_task_assign_skips_publish_without_wpl(component):
    component.send_to_other_system = lambda *args, **kwargs: {
        "success": True,
        "payload": {"mission": {}},
    }
    component.publish_to_other_system = pytest.fail

    assert component._handle_task_assign(
        {"payload": {"mission_id": "m-assign", "drone_id": "dr-7"}, "correlation_id": "corr-14"}
    ) is None


def test_handle_task_start_publishes_start_command(component):
    calls = []
    component.publish_to_other_system = lambda *args, **kwargs: calls.append((args, kwargs))

    component._handle_task_start(
        {
            "payload": {"mission_id": "m-start", "drone_id": "dr-8"},
            "correlation_id": "corr-13",
        }
    )

    assert calls == [
        (
            (
                ComponentTopics.GCS_DRONE_MANAGER,
                "mission.start",
                {"mission_id": "m-start", "drone_id": "dr-8"},
            ),
            {"correlation_id": "corr-13"},
        )
    ]
