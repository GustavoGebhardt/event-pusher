import json
import logging
import os

from event_pusher.calendar_client import GoogleCalendarClient
from event_pusher.validator import validate_event_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# reused across warm invocations, avoids re-fetching the secret every call
_calendar_client: GoogleCalendarClient | None = None


def _get_calendar_client() -> GoogleCalendarClient:
    global _calendar_client
    if _calendar_client is None:
        _calendar_client = GoogleCalendarClient(secret_name=os.environ["GOOGLE_SECRET_NAME"])
    return _calendar_client


def lambda_handler(event: dict, context) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "bad_request", "message": "Request body must be valid JSON"})

    try:
        validated = validate_event_request(body)
    except ValueError as exc:
        return _response(422, {"error": "validation_error", "message": str(exc)})

    try:
        created = _get_calendar_client().create_event(validated)
    except RuntimeError as exc:
        logger.error("Calendar error: %s", exc)
        return _response(502, {"error": "calendar_error", "message": str(exc)})
    except Exception:
        logger.exception("Unexpected error creating calendar event")
        return _response(500, {"error": "internal_error", "message": "Unexpected error"})

    logger.info("Event created: %s", created.get("event_id"))
    return _response(201, created)


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
