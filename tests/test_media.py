from recogni.media import _parse_rate, format_duration


def test_format_duration_uses_hours_minutes_seconds():
    assert format_duration(3661.9) == "01:01:01"


def test_format_duration_handles_negative_values():
    assert format_duration(-3) == "00:00:00"


def test_parse_rate_fraction():
    assert _parse_rate("24000/1001") == 24000 / 1001


def test_parse_rate_unknown_values():
    assert _parse_rate("0/0") is None
    assert _parse_rate(None) is None


from recogni.scenes import build_scenes, parse_scene_timestamps


def test_parse_scene_timestamps_extracts_unique_in_range_points():
    log = "[showinfo] pts_time:2.500\\n[showinfo] pts_time:5.000\\n[showinfo] pts_time:5.000\\n[showinfo] pts_time:12.000"
    assert parse_scene_timestamps(log, 10.0) == [2.5, 5.0]


def test_build_scenes_spans_entire_video_without_gaps():
    scenes = build_scenes([3.0, 7.5], 10.0)
    assert [(s.start_seconds, s.end_seconds) for s in scenes] == [(0.0, 3.0), (3.0, 7.5), (7.5, 10.0)]


def test_build_scenes_ignores_invalid_and_duplicate_cuts():
    scenes = build_scenes([-1, 0, 4, 4, 12], 8)
    assert [(s.start_seconds, s.end_seconds) for s in scenes] == [(0.0, 4.0), (4.0, 8.0)]


def test_build_scenes_short_video_without_cuts():
    scenes = build_scenes([], 1.25)
    assert len(scenes) == 1
    assert scenes[0].duration_seconds == 1.25
