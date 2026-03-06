import pytest
import json

from sdk.wpl_generator import (
    points_to_wpl,
    json_to_wpl,
    expand_two_points_to_path,
)


def test_expand_two_points_segments_5_produces_6_points():
    points = [
        {"lat": 10, "lon": 20, "alt": 50, "param1": 11, "param2": 5, "param3": 33, "param4": 123},
        {"lat": 20, "lon": 40, "alt": 150, "param1": 44, "param2": 7, "param3": 66, "param4": 456},
    ]

    path = expand_two_points_to_path(points, segments=5)
    assert len(path) == 6

    assert path[0]["lat"] == 10.0
    assert path[0]["lon"] == 20.0
    assert path[0]["alt"] == 50.0

    assert path[5]["lat"] == 20.0
    assert path[5]["lon"] == 40.0
    assert path[5]["alt"] == 150.0

    assert path[1]["lat"] == 12.0
    assert path[1]["lon"] == 24.0
    assert path[1]["alt"] == 70.0  # 50 + 0.2*(150-50)


def test_expand_two_points_params_policy_start_mid_end():
    start = {"lat": 0, "lon": 0, "alt": 10, "param1": 1, "param2": 5, "param3": 3, "param4": 999}
    end = {"lat": 10, "lon": 10, "alt": 20, "param1": 2, "param2": 7, "param3": 4, "param4": 888}

    path = expand_two_points_to_path([start, end], segments=5)

    # start: param1..3 from start, param4 forced to 0
    assert path[0]["param1"] == 1.0
    assert path[0]["param2"] == 5.0
    assert path[0]["param3"] == 3.0
    assert path[0]["param4"] == 0.0

    # middle: param1=0, param2=start.param2, param3=0, param4=0
    assert path[1]["param1"] == 0.0
    assert path[1]["param2"] == 5.0
    assert path[1]["param3"] == 0.0
    assert path[1]["param4"] == 0.0

    # end: param1..3 from end, param4 forced to 0
    assert path[5]["param1"] == 2.0
    assert path[5]["param2"] == 7.0
    assert path[5]["param3"] == 4.0
    assert path[5]["param4"] == 0.0


def test_expand_requires_exactly_two_points():
    with pytest.raises(ValueError, match="exactly 2 points"):
        expand_two_points_to_path([], segments=5)

    with pytest.raises(ValueError, match="exactly 2 points"):
        expand_two_points_to_path(
            [{"lat": 0, "lon": 0, "alt": 1, "param1": 0, "param2": 5, "param3": 0, "param4": 0}],
            segments=5,
        )

    with pytest.raises(ValueError, match="exactly 2 points"):
        expand_two_points_to_path([{}, {}, {}], segments=5)


def test_expand_segments_must_be_positive():
    start = {"lat": 0, "lon": 0, "alt": 10, "param1": 0, "param2": 5, "param3": 0, "param4": 0}
    end = {"lat": 1, "lon": 1, "alt": 10, "param1": 0, "param2": 5, "param3": 0, "param4": 0}

    with pytest.raises(ValueError, match="Segments"):
        expand_two_points_to_path([start, end], segments=0)


def test_expand_start_and_end_must_be_different():
    # lat/lon совпадают -- маршрут нулевой длины 
    start = {"lat": 59.9, "lon": 30.3, "alt": 50, "param1": 0, "param2": 5, "param3": 0, "param4": 0}
    end = {"lat": 59.9, "lon": 30.3, "alt": 100, "param1": 0, "param2": 7, "param3": 0, "param4": 0}

    with pytest.raises(ValueError, match="Start and end points must be different"):
        expand_two_points_to_path([start, end], segments=5)


def test_expand_missing_required_param2_in_start_raises():
    start = {"lat": 0, "lon": 0, "alt": 10, "param1": 0, "param3": 0, "param4": 0}  # нет param2
    end = {"lat": 1, "lon": 1, "alt": 10, "param1": 0, "param2": 5, "param3": 0, "param4": 0}

    with pytest.raises(ValueError, match="missing required field 'param2'"):
        expand_two_points_to_path([start, end], segments=5)


def test_expand_missing_required_param1_in_end_raises():
    start = {"lat": 0, "lon": 0, "alt": 10, "param1": 0, "param2": 5, "param3": 0, "param4": 0}
    end = {"lat": 1, "lon": 1, "alt": 10, "param2": 5, "param3": 0, "param4": 0}  # нет param1

    with pytest.raises(ValueError, match="missing required field 'param1'"):
        expand_two_points_to_path([start, end], segments=5)


@pytest.mark.parametrize(
    "which, field, value, error",
    [
        ("start", "lat", 999, "Latitude out of range"),
        ("start", "lon", 999, "Longitude out of range"),
        ("end", "lat", 999, "Latitude out of range"),
        ("end", "lon", 999, "Longitude out of range"),
    ],
)
def test_expand_invalid_coordinates_raise(which, field, value, error):
    start = {"lat": 0, "lon": 0, "alt": 10, "param1": 0, "param2": 5, "param3": 0, "param4": 0}
    end = {"lat": 10, "lon": 10, "alt": 20, "param1": 0, "param2": 5, "param3": 0, "param4": 0}

    if which == "start":
        start[field] = value
    else:
        end[field] = value

    with pytest.raises(ValueError, match=error):
        expand_two_points_to_path([start, end], segments=5)


def test_expand_negative_alt_raises():
    start = {"lat": 0, "lon": 0, "alt": 10, "param1": 0, "param2": 5, "param3": 0, "param4": 0}
    end = {"lat": 10, "lon": 10, "alt": -1, "param1": 0, "param2": 5, "param3": 0, "param4": 0}

    with pytest.raises(ValueError, match="Altitude must be >=0"):
        expand_two_points_to_path([start, end], segments=5)


def test_expand_start_or_end_not_dict_raises():
    start = {"lat": 0, "lon": 0, "alt": 10, "param1": 0, "param2": 5, "param3": 0, "param4": 0}
    with pytest.raises(ValueError, match="must be dict objects"):
        expand_two_points_to_path([start, 123], segments=5)


def test_points_to_wpl_successful_generation_6_points():
    # уже expanded points (6 штук), проверяем формат WPL
    points = [
        {"lat": 1, "lon": 2, "alt": 3, "param1": 0, "param2": 5, "param3": 0, "param4": 0},
        {"lat": 4, "lon": 5, "alt": 6, "param1": 0, "param2": 5, "param3": 0, "param4": 0},
        {"lat": 7, "lon": 8, "alt": 9, "param1": 0, "param2": 5, "param3": 0, "param4": 0},
        {"lat": 10, "lon": 11, "alt": 12, "param1": 0, "param2": 5, "param3": 0, "param4": 0},
        {"lat": 13, "lon": 14, "alt": 15, "param1": 0, "param2": 5, "param3": 0, "param4": 0},
        {"lat": 16, "lon": 17, "alt": 18, "param1": 0, "param2": 5, "param3": 0, "param4": 0},
    ]

    wpl = points_to_wpl(points, frame=3)
    assert wpl.startswith("QGC WPL 110\n")

    lines = wpl.strip().splitlines()
    assert len(lines) == 1 + 6  # header + 6 points
    assert lines[0] == "QGC WPL 110"

    # проверим все строки миссии: в каждой 12 полей
    for idx in range(1, 7):
        fields = lines[idx].split("\t")
        assert len(fields) == 12

    # current только у первой точки
    fields0 = lines[1].split("\t")
    fields1 = lines[2].split("\t")
    assert fields0[1] == "1"
    assert fields1[1] == "0"

    # frame/command/autocontinue
    assert fields0[2] == "3"
    assert fields0[3] == "16"
    assert fields0[11] == "1"


def test_points_to_wpl_empty_points_raises():
    with pytest.raises(ValueError, match="Points array is empty"):
        points_to_wpl([], frame=3)


@pytest.mark.parametrize("missing_field", ["lat", "lon", "alt"])
def test_points_to_wpl_missing_required_fields(missing_field):
    point = {
        "lat": 59.9,
        "lon": 30.3,
        "alt": 80,
        "param1": 0,
        "param2": 5,
        "param3": 0,
        "param4": 0,
    }

    del point[missing_field]

    with pytest.raises(ValueError, match=f"missing required field '{missing_field}'"):
        points_to_wpl([point])


@pytest.mark.parametrize("param_field", ["param1", "param2", "param3", "param4"])
def test_points_to_wpl_param_fields_must_be_numbers(param_field):
    point = {
        "lat": 59.9,
        "lon": 30.3,
        "alt": 80,
        "param1": 0,
        "param2": 5,
        "param3": 0,
        "param4": 0,
    }
    point[param_field] = "oops"

    with pytest.raises(ValueError, match=f"Field '{param_field}' must be a number"):
        points_to_wpl([point], frame=3)


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("lat", 999, "Latitude out of range"),
        ("lon", 999, "Longitude out of range"),
    ],
)
def test_points_to_wpl_invalid_coordinates(field, value, error):
    point = {
        "lat": 59.9,
        "lon": 30.3,
        "alt": 80,
        "param1": 0,
        "param2": 5,
        "param3": 0,
        "param4": 0,
    }

    point[field] = value

    with pytest.raises(ValueError, match=error):
        points_to_wpl([point], frame=3)


def test_points_to_wpl_negative_alt_raises():
    points = [{"lat": 59.9, "lon": 30.3, "alt": -1, "param1": 0, "param2": 5, "param3": 0, "param4": 0}]
    with pytest.raises(ValueError, match="Altitude must be >=0"):
        points_to_wpl(points, frame=3)


def test_json_to_wpl_file_created_and_has_7_lines(tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.wpl"

    points = [
        {"lat": 59.9, "lon": 30.3, "alt": 50, "param1": 0, "param2": 5, "param3": 0, "param4": 123},
        {"lat": 59.8, "lon": 30.2, "alt": 100, "param1": 0, "param2": 7, "param3": 0, "param4": 456},
    ]
    input_file.write_text(json.dumps(points), encoding="utf-8")

    json_to_wpl(str(input_file), str(output_file), frame=3, segments=5)

    assert output_file.exists()
    assert output_file.stat().st_size > 0

    content = output_file.read_text(encoding="utf-8")
    assert content.startswith("QGC WPL 110\n")

    lines = content.strip().splitlines()
    assert len(lines) == 1 + 6  # header + 6 points

    fields0 = lines[1].split("\t")
    assert fields0[2] == "3"
    assert fields0[3] == "16"


def test_json_to_wpl_interpolates_20_percent_point(tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.wpl"

    points = [
        {"lat": 10, "lon": 20, "alt": 50, "param1": 0, "param2": 5, "param3": 0, "param4": 123},
        {"lat": 20, "lon": 40, "alt": 150, "param1": 0, "param2": 7, "param3": 0, "param4": 456},
    ]
    input_file.write_text(json.dumps(points), encoding="utf-8")

    json_to_wpl(str(input_file), str(output_file), frame=3, segments=5)

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()

    # строка 0 header
    # строка 1 index=0 (start)
    # строка 2 index=1 (t=0.2)
    fields = lines[2].split("\t")

    assert fields[8] == "12.0"   # lat
    assert fields[9] == "24.0"   # lon
    assert fields[10] == "70.0"  # alt

    # param4 должен быть 0 на промежуточных
    assert fields[7] == "0.0"


def test_json_to_wpl_input_file_not_found_raises(tmp_path):
    missing_input = tmp_path / "missing.json"
    output_file = tmp_path / "out.wpl"
    with pytest.raises(FileNotFoundError, match="Input file not found"):
        json_to_wpl(str(missing_input), str(output_file), frame=3, segments=5)


def test_json_to_wpl_output_path_not_writable_raises(tmp_path):
    input_file = tmp_path / "input.json"
    bad_output = tmp_path / "no_such_dir" / "out.wpl"

    points = [
        {"lat": 59.9, "lon": 30.3, "alt": 50, "param1": 0, "param2": 5, "param3": 0, "param4": 0},
        {"lat": 59.8, "lon": 30.2, "alt": 100, "param1": 0, "param2": 5, "param3": 0, "param4": 0},
    ]
    input_file.write_text(json.dumps(points), encoding="utf-8")

    with pytest.raises(OSError):
        json_to_wpl(str(input_file), str(bad_output), frame=3, segments=5)


def test_json_to_wpl_invalid_json_raises(tmp_path):
    input_file = tmp_path / "bad.json"
    output_file = tmp_path / "out.wpl"

    input_file.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        json_to_wpl(str(input_file), str(output_file), frame=3, segments=5)


def test_json_to_wpl_json_root_not_list_raises(tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "out.wpl"

    input_file.write_text(json.dumps({"a": 1}), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON root must be a list of points"):
        json_to_wpl(str(input_file), str(output_file), frame=3, segments=5)


def test_json_to_wpl_list_not_two_points_raises(tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "out.wpl"

    input_file.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(ValueError, match="Expected exactly 2 points"):
        json_to_wpl(str(input_file), str(output_file), frame=3, segments=5)