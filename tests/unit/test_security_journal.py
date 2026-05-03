"""Tests for sdk.security_journal — JournalRecorder + JournalRecord."""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

import pytest

from sdk.security_journal import (
    LOG_EVENT_ACTION,
    MAX_MESSAGE_LEN,
    SEVERITY_LEVELS,
    SEVERITY_RANK,
    JournalRecord,
    JournalRecorder,
)


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _make_recorder(tmp_path: Path, **overrides) -> tuple[JournalRecorder, Path]:
    file_path = tmp_path / "journal.ndjson"
    kwargs = dict(file_path=str(file_path), service="dronePort", service_id=1)
    kwargs.update(overrides)
    return JournalRecorder(**kwargs), file_path


def test_log_event_action_constant():
    assert LOG_EVENT_ACTION == "log_event"


def test_severity_levels_order_matches_syslog():
    assert SEVERITY_LEVELS == (
        "debug", "info", "notice", "warning", "error",
        "critical", "alert", "emergency",
    )
    assert SEVERITY_RANK["debug"] < SEVERITY_RANK["emergency"]


def test_write_appends_valid_ndjson(tmp_path):
    recorder, file_path = _make_recorder(tmp_path)
    record = recorder.build_record(
        severity="warning",
        source_sender="components.drone_manager",
        source_component="drone_manager",
        source_action="request_landing.no_free_ports",
        message="Landing denied",
        details={"drone_id": "DR-1"},
    )
    assert record is not None
    recorder.write(record)

    lines = _read_lines(file_path)
    assert len(lines) == 1
    entry = lines[0]
    assert entry["severity"] == "warning"
    assert entry["service"] == "dronePort"
    assert entry["service_id"] == 1
    assert entry["event_type"] == "safety_event"
    assert entry["source_component"] == "drone_manager"
    assert entry["source_action"] == "request_landing.no_free_ports"
    assert entry["details"] == {"drone_id": "DR-1"}
    assert isinstance(entry["timestamp_ms"], int)
    assert entry["timestamp_iso"].endswith("+00:00")


def test_log_helper_writes_one_line(tmp_path):
    recorder, file_path = _make_recorder(tmp_path)
    recorder.log(
        severity="critical",
        source_sender="systems.drone_port",
        source_component="drone_port_security_monitor",
        source_action="proxy_request.denied",
        message="Policy denied",
        details={"target_action": "request_landing"},
    )
    lines = _read_lines(file_path)
    assert len(lines) == 1
    assert lines[0]["severity"] == "critical"


def test_invalid_severity_drops_record(tmp_path, caplog):
    recorder, _ = _make_recorder(tmp_path)
    with caplog.at_level(logging.WARNING):
        record = recorder.build_record(
            severity="VERY-BAD",
            source_sender="x",
            source_component="x",
            source_action="x",
            message="x",
        )
    assert record is None
    assert "invalid severity" in caplog.text


def test_min_severity_filter_skips_below(tmp_path):
    recorder, file_path = _make_recorder(tmp_path, min_severity="warning")
    recorder.log(
        severity="info",
        source_sender="s", source_component="c", source_action="a",
        message="should be skipped",
    )
    recorder.log(
        severity="warning",
        source_sender="s", source_component="c", source_action="a",
        message="kept",
    )
    recorder.log(
        severity="critical",
        source_sender="s", source_component="c", source_action="a",
        message="kept",
    )
    lines = _read_lines(file_path)
    assert [entry["severity"] for entry in lines] == ["warning", "critical"]


def test_message_truncated_to_max_len(tmp_path):
    recorder, file_path = _make_recorder(tmp_path)
    big = "x" * (MAX_MESSAGE_LEN + 500)
    recorder.log(
        severity="info",
        source_sender="s", source_component="c", source_action="a",
        message=big,
    )
    entry = _read_lines(file_path)[0]
    assert len(entry["message"]) == MAX_MESSAGE_LEN


def test_concurrent_writes_serialize(tmp_path):
    recorder, file_path = _make_recorder(tmp_path)
    threads_n = 8
    per_thread = 25

    def worker(idx: int) -> None:
        for n in range(per_thread):
            recorder.log(
                severity="info",
                source_sender="s",
                source_component="c",
                source_action=f"t{idx}.n{n}",
                message=f"thread {idx} item {n}",
            )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(threads_n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = _read_lines(file_path)
    assert len(lines) == threads_n * per_thread
    # Каждая строка — самостоятельный валидный JSON (значит запись была атомарной).
    for entry in lines:
        assert "source_action" in entry


def test_io_error_does_not_raise(tmp_path, monkeypatch, caplog):
    recorder, _ = _make_recorder(tmp_path)
    record = recorder.build_record(
        severity="info",
        source_sender="s", source_component="c", source_action="a",
        message="m",
    )
    assert record is not None

    def _boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", _boom)
    with caplog.at_level(logging.ERROR):
        recorder.write(record)  # must not raise
    assert "journal: write failed" in caplog.text


def test_empty_file_path_is_no_op(tmp_path):
    recorder = JournalRecorder(file_path="", service="dronePort", service_id=1)
    record = recorder.build_record(
        severity="info",
        source_sender="s", source_component="c", source_action="a",
        message="m",
    )
    assert record is not None
    recorder.write(record)  # must not raise, must not create files
    assert not any(tmp_path.iterdir())


def test_dataclass_default_event_type():
    rec = JournalRecord(
        timestamp_iso="t", timestamp_ms=0,
        service="GCS", service_id=2,
        severity="info", message="m",
        source_component="c", source_sender="s", source_action="a",
    )
    assert rec.event_type == "safety_event"
    assert rec.details == {}


def test_creates_parent_dir(tmp_path):
    nested = tmp_path / "a" / "b" / "journal.ndjson"
    recorder = JournalRecorder(file_path=str(nested), service="GCS", service_id=2)
    recorder.log(
        severity="notice",
        source_sender="s", source_component="c", source_action="port.reserved",
        message="ok",
    )
    assert nested.exists()
    assert _read_lines(nested)[0]["service"] == "GCS"
