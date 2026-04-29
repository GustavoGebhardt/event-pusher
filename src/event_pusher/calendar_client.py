import boto3
import json
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CALENDAR_ID = "primary"


class GoogleCalendarClient:
    def __init__(self, secret_name: str):
        self._secret_name = secret_name
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        sm = boto3.client("secretsmanager")
        secret = json.loads(
            sm.get_secret_value(SecretId=self._secret_name)["SecretString"]
        )

        creds = Credentials(
            token=None,
            refresh_token=secret["refresh_token"],
            client_id=secret["client_id"],
            client_secret=secret["client_secret"],
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )

        # cache_discovery=False avoids filesystem writes inside Lambda
        self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def create_event(self, validated: dict) -> dict:
        body = {
            "summary": validated["title"],
            "start": {"dateTime": validated["starts_at"], "timeZone": validated["timezone"]},
            "end": {"dateTime": validated["ends_at"], "timeZone": validated["timezone"]},
        }

        if validated.get("description"):
            body["description"] = validated["description"]

        if validated.get("location"):
            body["location"] = validated["location"]

        if validated.get("attendees"):
            body["attendees"] = [{"email": e} for e in validated["attendees"]]

        try:
            service = self._get_service()
            created = service.events().insert(calendarId=CALENDAR_ID, body=body).execute()
        except HttpError as e:
            logger.error("Google Calendar API error: %s %s", e.status_code, e.reason)
            raise RuntimeError(f"Google Calendar API error ({e.status_code}): {e.reason}") from e

        return {
            "event_id": created["id"],
            "html_link": created.get("htmlLink"),
            "title": created.get("summary"),
            "starts_at": created["start"].get("dateTime"),
            "ends_at": created["end"].get("dateTime"),
        }
