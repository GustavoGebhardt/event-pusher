import os
from datetime import datetime, timezone, timedelta
from typing import Optional


def validate_event_request(body: dict) -> dict:
    starts_at = _parse_datetime(body.get("starts_at"), "starts_at")
    ends_at = _parse_datetime(body.get("ends_at"), "ends_at")

    if starts_at >= ends_at:
        raise ValueError("starts_at must be before ends_at")

    duration = ends_at - starts_at
    min_minutes = int(os.environ.get("MIN_DURATION_MINUTES", "5"))
    max_hours = int(os.environ.get("MAX_DURATION_HOURS", "8"))

    if duration < timedelta(minutes=min_minutes):
        raise ValueError(f"Event duration must be at least {min_minutes} minutes")

    if duration > timedelta(hours=max_hours):
        raise ValueError(f"Event duration cannot exceed {max_hours} hours")

    now = datetime.now(timezone.utc)
    allow_past = os.environ.get("ALLOW_PAST_EVENTS", "false").lower() == "true"
    if not allow_past and ends_at <= now:
        raise ValueError("Cannot create events that end in the past")

    max_future_days = int(os.environ.get("MAX_FUTURE_DAYS", "365"))
    if starts_at > now + timedelta(days=max_future_days):
        raise ValueError(f"Cannot schedule events more than {max_future_days} days in advance")

    title = (body.get("title") or "").strip() or os.environ.get("DEFAULT_TITLE", "Ocupado")

    description = (body.get("description") or "").strip()
    if len(description) > 8000:
        raise ValueError("description cannot exceed 8000 characters")

    location = (body.get("location") or "").strip()
    if len(location) > 1000:
        raise ValueError("location cannot exceed 1000 characters")

    attendees = body.get("attendees") or []
    if len(attendees) > 20:
        raise ValueError("Cannot invite more than 20 attendees")

    timezone_name = (body.get("timezone") or "").strip() or os.environ.get("DEFAULT_TIMEZONE", "America/Sao_Paulo")

    return {
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "title": title,
        "description": description,
        "location": location,
        "attendees": attendees,
        "timezone": timezone_name,
    }


def _parse_datetime(value: Optional[str], field_name: str) -> datetime:
    if not value:
        raise ValueError(f"{field_name} is required")

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"{field_name} must be a valid ISO 8601 datetime (e.g., 2026-04-30T14:00:00-03:00)"
        )

    if dt.tzinfo is None:
        raise ValueError(
            f"{field_name} must include timezone offset (e.g., 2026-04-30T14:00:00-03:00)"
        )

    return dt
