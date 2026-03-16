import hashlib
import json

import pytest

from systems.gcs.src.contracts import MissionStatus
from systems.gcs.src.path_planner.src.path_planner import PathPlannerComponent
from systems.gcs.src.path_planner.topics import ComponentTopics, PathPlannerActions


@pytest.fixture
def component(mock_bus):
    return PathPlannerComponent(component_id="path-planner", bus=mock_bus)
    

def test_normalize_point_accepts_aliases(component):
    point = component._normalize_point({"latitude": "55.75", "lng": "37.61", "altitude": "120"})

    assert point == {"lat": 55.75, "lon": 37.61, "alt": 120.0}


def test_normalize_point_rejects_invalid_payload(component):
    assert component._normalize_point(None) is None
    assert component._normalize_point({"lat": "bad", "lon": 37.0}) is None
    assert component._normalize_point({"lat": 10.0}) is None


def test_extract_start_end_normalizes_task_points(component):
    start, end = component._extract_start_end(
        {
            "start_point": {"lat": 1, "lon": 2, "alt": 3},
            "end_point": {"latitude": 4, "longitude": 5, "altitude": 6},
        }
    )

    assert start == {"lat": 1.0, "lon": 2.0, "alt": 3.0}
    assert end == {"lat": 4.0, "lon": 5.0, "alt": 6.0}


def test_build_stub_route_returns_round_trip(component):
    start = {"lat": 10.0, "lon": 20.0, "alt": 30.0}
    end = {"lat": 16.0, "lon": 26.0, "alt": 36.0}

    route = component._build_stub_route(start, end)

    assert len(route) == 7
    assert route[0] == start
    assert route[3] == end
    assert route[-1] == start
    assert route[1] == {"lat": 11.98, "lon": 21.98, "alt": 31.98}


def test_handle_path_plan_saves_mission_and_returns_route(component):
    calls = []

    def fake_publish(target_topic, action, payload, correlation_id=None):
        calls.append((target_topic, action, payload, correlation_id))

    component.publish_to_other_system = fake_publish
    message = {
        "payload": {
            "mission_id": "m-plan",
            "task": {
                "start_point": {"lat": 1.0, "lon": 2.0, "alt": 3.0},
                "end_point": {"lat": 4.0, "lon": 5.0, "alt": 6.0},
            },
        },
        "correlation_id": "corr-1",
    }

    result = component._handle_path_plan(message)

    expected_waypoints = component._build_stub_route(
        {"lat": 1.0, "lon": 2.0, "alt": 3.0},
        {"lat": 4.0, "lon": 5.0, "alt": 6.0},
    )
    expected_signature = hashlib.sha256(
        json.dumps(expected_waypoints, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert result["mission_id"] == "m-plan"
    assert result["waypoints"] == expected_waypoints
    assert result["signature"] == expected_signature
    assert calls[0][0] == ComponentTopics.GCS_MISSION_STORE
    assert calls[0][1] == "store.save_mission"
    assert calls[0][2]["mission"]["status"] == MissionStatus.CREATED
    assert calls[0][3] == "corr-1"


def test_handle_path_plan_sets_timestamps_on_saved_mission(component):
    calls = []
    component.publish_to_other_system = lambda *args, **kwargs: calls.append((args, kwargs))

    component._handle_path_plan(
        {
            "payload": {
                "mission_id": "m-time",
                "task": {
                    "start_point": {"lat": 1.0, "lon": 2.0},
                    "end_point": {"lat": 3.0, "lon": 4.0},
                },
            }
        }
    )

    saved_mission = calls[0][0][2]["mission"]
    assert saved_mission["created_at"]
    assert saved_mission["updated_at"]
    assert saved_mission["assigned_drone"] is None
