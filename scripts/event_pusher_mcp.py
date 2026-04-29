from mcp.server.fastmcp import FastMCP
import requests
import os

mcp = FastMCP("event-pusher")

API_URL = os.environ["EVENT_PUSHER_API_URL"]
API_KEY = os.environ["EVENT_PUSHER_API_KEY"]


def post_event(payload: dict) -> dict:
    r = requests.post(
        f"{API_URL}/events",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool(
    description="""
Create a calendar event in Google Calendar via Event Pusher API.

Use this tool when the user wants to:
- schedule an event
- block time in calendar
- create an appointment or meeting

Returns the created event with id and link.
"""
)
def create_event(
    starts_at: str,
    ends_at: str,
    title: str = "Ocupado",
    timezone: str = "America/Sao_Paulo",
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
):
    """
    Parameters:

    REQUIRED:
    - starts_at (str): ISO 8601 datetime string for event start (e.g. 2026-04-29T10:00:00-03:00)
    - ends_at (str): ISO 8601 datetime string for event end

    OPTIONAL:
    - title (str): Event title. Default: "Ocupado"
    - timezone (str): IANA timezone. Default: "America/Sao_Paulo"
    - description (str): Event description
    - location (str): Event location
    - attendees (list[str]): List of attendee emails
    """

    payload = {
        "starts_at": starts_at,
        "ends_at": ends_at,
        "title": title,
        "timezone": timezone,
    }

    if description:
        payload["description"] = description

    if location:
        payload["location"] = location

    if attendees:
        payload["attendees"] = attendees

    return post_event(payload)


if __name__ == "__main__":
    mcp.run()