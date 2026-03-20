import hashlib

import pytest

from systems.gcs.src.mission_converter.src.mission_converter import MissionConverterComponent
from systems.gcs.src.mission_converter.topics import MissionActions


@pytest.fixture
def component(mock_bus):
    return MissionConverterComponent(component_id="mission-converter", bus=mock_bus)


def test_extract_points_returns_waypoints_list(component):
    payload = {"waypoints": [{"lat": 1.0, "lon": 2.0}]}

    assert component._extract_points(payload) == payload["waypoints"]


def test_extract_points_returns_empty_list_for_invalid_payload(component):
    assert component._extract_points({"waypoints": "invalid"}) == []
    assert component._extract_points({}) == []


def test_to_wpl_formats_header_and_waypoints(component):
    points = [
        {"lat": 55.1, "lon": 37.2, "alt": 100, "params": {"p1": 7}, "command": 22},
        {"latitude": 55.2, "longitude": 37.3, "altitude": 110},
    ]

    result = component._to_wpl(points)

    lines = result.splitlines()
    assert lines[0] == "QGC WPL 110"
    assert lines[1] == "0\t1\t3\t22\t7\t0\t0\t0\t55.1\t37.2\t100\t1"
    assert lines[2] == "1\t0\t3\t16\t0\t0\t0\t0\t55.2\t37.3\t110\t1"


def test_handle_mission_prepare_returns_wpl_and_signature(component):
    mission = {
        "waypoints": [
            {"lat": 10.0, "lon": 20.0, "alt": 30.0},
            {"lat": 11.0, "lon": 21.0, "alt": 31.0},
        ]
    }
    component.send_to_other_system = lambda *args, **kwargs: {
        "success": True,
        "payload": {"mission": mission},
    }

    result = component._handle_mission_prepare({"payload": {"mission_id": "m-1"}})

    expected_wpl = component._to_wpl(mission["waypoints"])
    expected_signature = hashlib.sha256(expected_wpl.encode("utf-8")).hexdigest()
    assert result == {
        "mission": {
            "mission_id": "m-1",
            "wpl": expected_wpl,
            "signature": expected_signature,
        }
    }


def test_handle_mission_prepare_returns_error_when_store_unavailable(component):
    component.send_to_other_system = lambda *args, **kwargs: None

    result = component._handle_mission_prepare({"payload": {"mission_id": "m-404"}})

    assert result == {"mission_id": "m-404", "error": "mission store unavailable"}
