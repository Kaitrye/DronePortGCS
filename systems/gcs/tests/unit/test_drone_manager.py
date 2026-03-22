import pytest

from systems.gcs.topics import DroneActions, DroneTopics
from systems.gcs.src.contracts import DroneStatus, MissionStatus
from systems.gcs.src.drone_manager.src.drone_manager import DroneManagerComponent
from systems.gcs.src.drone_manager.topics import ComponentTopics
from systems.gcs.src.drone_store.topics import DroneStoreActions
from systems.gcs.src.mission_store.topics import MissionStoreActions


@pytest.fixture
def component(mock_bus):
    return DroneManagerComponent(component_id="drone-manager", bus=mock_bus)


def test_handle_mission_upload(component, mock_bus):
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

    assert mock_bus.publish.call_count == 3
    assert mock_bus.publish.call_args_list[0].args == (
        DroneTopics.DRONE,
        {
            "action": DroneActions.UPLOAD_MISSION,
            "sender": "drone-manager",
            "payload": {"mission_id": "m-upload", "mission": "QGC WPL 110"},
            "correlation_id": "corr-3",
        },
    )
    assert mock_bus.publish.call_args_list[1].args == (
        ComponentTopics.GCS_MISSION_STORE,
        {
            "action": MissionStoreActions.UPDATE_MISSION,
            "sender": "drone-manager",
            "payload": {
                "mission_id": "m-upload",
                "fields": {
                    "assigned_drone": "dr-1", 
                    "status": MissionStatus.ASSIGNED
                },
            },
            "correlation_id": "corr-3",
        },
    )
    assert mock_bus.publish.call_args_list[2].args == (
        ComponentTopics.GCS_DRONE_STORE,
        {
            "action": DroneStoreActions.UPDATE_DRONE,
            "sender": "drone-manager",
            "payload": {
                "drone_id": "dr-1", 
                "status": DroneStatus.RESERVED
            },
            "correlation_id": "corr-3",
        },
    )


def test_handle_telemetry_save(component, mock_bus):
    component._handle_telemetry_save(
        {
            "payload": {"telemetry": {"drone_id": "dr-2"}},
            "correlation_id": "corr-4",
        }
    )

    assert mock_bus.publish.call_args.args == (
        ComponentTopics.GCS_DRONE_STORE,
        {
            "action": DroneStoreActions.SAVE_TELEMETRY,
            "sender": "drone-manager",
            "payload": {"telemetry": {"drone_id": "dr-2"}},
            "correlation_id": "corr-4",
        },
    )


def test_handle_mission_start(component, mock_bus):
    component._handle_mission_start(
        {
            "payload": {"mission_id": "m-run", "drone_id": "dr-3"},
            "correlation_id": "corr-5",
        }
    )

    assert mock_bus.publish.call_count == 3
    assert mock_bus.publish.call_args_list[0].args == (
        DroneTopics.DRONE,
        {
            "action": DroneActions.MISSION_START,
            "sender": "drone-manager",
            "payload": {},
            "correlation_id": "corr-5",
        },
    )
    assert mock_bus.publish.call_args_list[1].args == (
        ComponentTopics.GCS_MISSION_STORE,
        {
            "action": MissionStoreActions.UPDATE_MISSION,
            "sender": "drone-manager",
            "payload": {
                "mission_id": "m-run", 
                "fields": {
                    "status": MissionStatus.RUNNING
                }
            },
            "correlation_id": "corr-5",
        },
    )
    assert mock_bus.publish.call_args_list[2].args == (
        ComponentTopics.GCS_DRONE_STORE,
        {
            "action": DroneStoreActions.UPDATE_DRONE,
            "sender": "drone-manager",
            "payload": {
                "drone_id": "dr-3", 
                "status": DroneStatus.BUSY
            },
            "correlation_id": "corr-5",
        },
    )
