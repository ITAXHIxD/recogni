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
