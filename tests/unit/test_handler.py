import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta


def _event(body: dict) -> dict:
    return {"body": json.dumps(body)}


def _valid_body():
    now = datetime.now(timezone.utc)
    return {
        "starts_at": (now + timedelta(hours=1)).isoformat(),
        "ends_at": (now + timedelta(hours=2)).isoformat(),
    }


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("GOOGLE_SECRET_NAME", "event-pusher/google-credentials")
    monkeypatch.setenv("MIN_DURATION_MINUTES", "5")
    monkeypatch.setenv("MAX_DURATION_HOURS", "8")
    monkeypatch.setenv("MAX_FUTURE_DAYS", "365")
    monkeypatch.setenv("ALLOW_PAST_EVENTS", "false")
    monkeypatch.setenv("DEFAULT_TITLE", "Ocupado")
    monkeypatch.setenv("DEFAULT_TIMEZONE", "America/Sao_Paulo")


def test_returns_201_on_success():
    from event_pusher import handler

    handler._calendar_client = None
    mock_client = MagicMock()
    mock_client.create_event.return_value = {
        "event_id": "abc123",
        "html_link": "https://calendar.google.com/event?eid=abc123",
        "title": "Ocupado",
        "starts_at": _valid_body()["starts_at"],
        "ends_at": _valid_body()["ends_at"],
    }

    with patch("event_pusher.handler._get_calendar_client", return_value=mock_client):
        response = handler.lambda_handler(_event(_valid_body()), None)

    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["event_id"] == "abc123"


def test_returns_422_on_validation_error():
    from event_pusher import handler

    response = handler.lambda_handler(_event({"starts_at": "bad", "ends_at": "bad"}), None)

    assert response["statusCode"] == 422
    body = json.loads(response["body"])
    assert body["error"] == "validation_error"


def test_returns_400_on_invalid_json():
    from event_pusher import handler

    response = handler.lambda_handler({"body": "not-json"}, None)

    assert response["statusCode"] == 400


def test_returns_502_on_calendar_error():
    from event_pusher import handler

    handler._calendar_client = None
    mock_client = MagicMock()
    mock_client.create_event.side_effect = RuntimeError("Google Calendar API error (403): forbidden")

    with patch("event_pusher.handler._get_calendar_client", return_value=mock_client):
        response = handler.lambda_handler(_event(_valid_body()), None)

    assert response["statusCode"] == 502
    body = json.loads(response["body"])
    assert body["error"] == "calendar_error"
