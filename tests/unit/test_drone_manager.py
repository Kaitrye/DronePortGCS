import pytest

from systems.gcs.src.contracts import DroneStatus, MissionStatus
from systems.gcs.src.drone_manager.src.drone_manager import DroneManagerComponent
from systems.gcs.src.drone_manager.topics import ComponentTopics
from systems.gcs.src.drone_store.topics import DroneStoreActions
from systems.gcs.src.mission_store.topics import MissionStoreActions
from systems.gcs.src.topics import ExternalDroneActions, ExternalTopics


@pytest.fixture
def component(mock_bus):
    return DroneManagerComponent(component_id="drone-manager", bus=mock_bus)


def test_send_to_other_system_builds_request(component, mock_bus):
    component.send_to_other_system(
        ComponentTopics.GCS_MISSION_STORE,
        MissionStoreActions.GET_MISSION,
        {"mission_id": "m-1"},
        correlation_id="corr-1",
    )

    mock_bus.request.assert_called_once_with(
        ComponentTopics.GCS_MISSION_STORE,
        {
            "action": MissionStoreActions.GET_MISSION,
            "sender": "drone-manager",
            "payload": {"mission_id": "m-1"},
            "correlation_id": "corr-1",
        },
        timeout=10.0,
    )


def test_publish_to_other_system_builds_message(component, mock_bus):
    component.publish_to_other_system(
        ExternalTopics.DRONE,
        ExternalDroneActions.UPLOAD_MISSION,
        {"mission": "data"},
        correlation_id="corr-2",
    )

    mock_bus.publish.assert_called_once_with(
        ExternalTopics.DRONE,
        {
            "action": ExternalDroneActions.UPLOAD_MISSION,
            "sender": "drone-manager",
            "payload": {"mission": "data"},
            "correlation_id": "corr-2",
        },
    )


def test_handle_mission_upload(component):
    calls = []
    component.publish_to_other_system = lambda *args, **kwargs: calls.append((args, kwargs))

    component._handle_mission_upload(
        {
            "payload": {
                "mission_id": "m-upload",
                "drone_id": "dr-1",
                "wpl": "QGC WPL 110",
            },
            "correlation_id": "corr-3",
        }
    )

    assert len(calls) == 3
    assert calls[0][0] == (
        ExternalTopics.DRONE,
        ExternalDroneActions.UPLOAD_MISSION,
        {"mission_id": "m-upload", "mission": "QGC WPL 110"},
    )
    assert calls[1][0] == (
        ComponentTopics.GCS_MISSION_STORE,
        MissionStoreActions.UPDATE_MISSION,
        {
            "mission_id": "m-upload",
            "fields": {
                "assigned_drone": "dr-1", 
                "status": MissionStatus.ASSIGNED
            },
        },
    )
    assert calls[2][0] == (
        ComponentTopics.GCS_DRONE_STORE,
        DroneStoreActions.UPDATE_DRONE,
        {
            "drone_id": "dr-1", 
            "status": DroneStatus.RESERVED
        },
    )
    assert all(call[1]["correlation_id"] == "corr-3" for call in calls)


def test_handle_telemetry_save(component):
    calls = []
    component.publish_to_other_system = lambda *args, **kwargs: calls.append((args, kwargs))

    component._handle_telemetry_save(
        {
            "payload": {"telemetry": {"drone_id": "dr-2"}},
            "correlation_id": "corr-4",
        }
    )

    assert calls == [
        (
            (
                ComponentTopics.GCS_DRONE_STORE,
                DroneStoreActions.SAVE_TELEMETRY,
                {"telemetry": {"drone_id": "dr-2"}},
            ),
            {"correlation_id": "corr-4"},
        )
    ]


def test_handle_mission_start(component):
    calls = []
    component.publish_to_other_system = lambda *args, **kwargs: calls.append((args, kwargs))

    component._handle_mission_start(
        {
            "payload": {"mission_id": "m-run", "drone_id": "dr-3"},
            "correlation_id": "corr-5",
        }
    )

    assert len(calls) == 3
    assert calls[0][0] == (ExternalTopics.DRONE, ExternalDroneActions.MISSION_START, {})
    assert calls[1][0] == (
        ComponentTopics.GCS_MISSION_STORE,
        MissionStoreActions.UPDATE_MISSION,
        {
            "mission_id": "m-run", 
            "fields": {
                "status": MissionStatus.RUNNING
            }
        },
    )
    assert calls[2][0] == (
        ComponentTopics.GCS_DRONE_STORE,
        DroneStoreActions.UPDATE_DRONE,
        {
            "drone_id": "dr-3", 
            "status": DroneStatus.BUSY
        },
    )
