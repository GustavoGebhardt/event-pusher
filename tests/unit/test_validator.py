import pytest
from datetime import datetime, timezone, timedelta


def _future(hours=1, minutes=0):
    return (datetime.now(timezone.utc) + timedelta(hours=hours, minutes=minutes)).isoformat()


def _past(hours=1):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def _make(**kwargs):
    base = {"starts_at": _future(1), "ends_at": _future(2)}
    base.update(kwargs)
    return base


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("MIN_DURATION_MINUTES", "5")
    monkeypatch.setenv("MAX_DURATION_HOURS", "8")
    monkeypatch.setenv("MAX_FUTURE_DAYS", "365")
    monkeypatch.setenv("ALLOW_PAST_EVENTS", "false")
    monkeypatch.setenv("DEFAULT_TITLE", "Ocupado")
    monkeypatch.setenv("DEFAULT_TIMEZONE", "America/Sao_Paulo")


def test_valid_minimal_event():
    from event_pusher.validator import validate_event_request

    result = validate_event_request(_make())
    assert result["title"] == "Ocupado"
    assert result["timezone"] == "America/Sao_Paulo"
    assert result["attendees"] == []


def test_custom_title_is_used():
    from event_pusher.validator import validate_event_request

    result = validate_event_request(_make(title="Sprint review"))
    assert result["title"] == "Sprint review"


def test_blank_title_falls_back_to_default():
    from event_pusher.validator import validate_event_request

    result = validate_event_request(_make(title="   "))
    assert result["title"] == "Ocupado"


def test_missing_starts_at():
    from event_pusher.validator import validate_event_request

    with pytest.raises(ValueError, match="starts_at is required"):
        validate_event_request({"ends_at": _future(2)})


def test_missing_ends_at():
    from event_pusher.validator import validate_event_request

    with pytest.raises(ValueError, match="ends_at is required"):
        validate_event_request({"starts_at": _future(1)})


def test_starts_after_ends():
    from event_pusher.validator import validate_event_request

    with pytest.raises(ValueError, match="starts_at must be before ends_at"):
        validate_event_request({"starts_at": _future(2), "ends_at": _future(1)})


def test_duration_too_short():
    from event_pusher.validator import validate_event_request

    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="at least 5 minutes"):
        validate_event_request({
            "starts_at": (now + timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(hours=1, minutes=3)).isoformat(),
        })


def test_duration_too_long():
    from event_pusher.validator import validate_event_request

    with pytest.raises(ValueError, match="cannot exceed 8 hours"):
        validate_event_request({"starts_at": _future(1), "ends_at": _future(10)})


def test_event_ends_in_past():
    from event_pusher.validator import validate_event_request

    with pytest.raises(ValueError, match="in the past"):
        validate_event_request({"starts_at": _past(3), "ends_at": _past(1)})


def test_allow_past_events_env(monkeypatch):
    from event_pusher.validator import validate_event_request

    monkeypatch.setenv("ALLOW_PAST_EVENTS", "true")
    result = validate_event_request({"starts_at": _past(3), "ends_at": _past(1)})
    assert result["title"] == "Ocupado"


def test_no_timezone_raises():
    from event_pusher.validator import validate_event_request

    with pytest.raises(ValueError, match="must include timezone"):
        validate_event_request({
            "starts_at": "2026-05-01T14:00:00",
            "ends_at": "2026-05-01T15:00:00",
        })


def test_too_many_attendees():
    from event_pusher.validator import validate_event_request

    with pytest.raises(ValueError, match="20 attendees"):
        validate_event_request(_make(attendees=[f"user{i}@x.com" for i in range(21)]))


def test_too_far_in_future(monkeypatch):
    from event_pusher.validator import validate_event_request

    monkeypatch.setenv("MAX_FUTURE_DAYS", "30")
    with pytest.raises(ValueError, match="30 days in advance"):
        validate_event_request({"starts_at": _future(hours=24 * 31), "ends_at": _future(hours=24 * 31 + 1)})
