# event-pusher

A serverless HTTP API that creates events on a personal Google Calendar. Send a start time, an end time, and an optional title — the service books a block on your calendar and returns the event link.

Built with AWS API Gateway REST, AWS Lambda (Python 3.12), AWS Secrets Manager, and the Google Calendar API. Deployed with AWS SAM and managed with [uv](https://github.com/astral-sh/uv).

---

## Table of Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Configuration Parameters](#configuration-parameters)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Development](#development)

---

## Architecture

```
Client
  │
  │  POST /events  ·  x-api-key: <key>
  ▼
┌─────────────────────────────────────────────────┐
│               API Gateway REST                  │
│  • API key validation               → 403       │
│  • Throttle (burst / rate / quota)  → 429       │
│  • JSON schema validation           → 400       │
└─────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────┐
│                   Lambda                        │
│  1. Business validation (dates, duration, etc.) │
│  2. Fetch Google credentials from Secrets Mgr   │
│  3. Create event via Google Calendar API        │
└─────────────────────────────────────────────────┘
  │
  ▼
Google Calendar API  →  Event created on primary calendar
```

The Google service client is initialized once and held in memory across warm invocations — Secrets Manager is called only on cold starts.

---

## Project Structure

```
event-pusher/
│
├── template.yaml                   # SAM infrastructure definition
├── samconfig.toml                  # SAM deploy defaults
├── pyproject.toml                  # Python project and dependencies
├── Makefile                        # SAM build target using uv
│
├── src/
│   └── event_pusher/
│       ├── handler.py              # Lambda entry point
│       ├── validator.py            # Business rule validation
│       └── calendar_client.py     # Google Calendar API client
│
├── scripts/
│   └── setup_google_auth.py       # One-time OAuth2 setup helper
│
└── tests/
    └── unit/
        ├── test_validator.py
        └── test_handler.py
```

---

## API Reference

### `POST /events`

**Required header**

```
x-api-key: <your-api-key>
```

**Request body**

| Field | Type | Required | Description |
|---|---|---|---|
| `starts_at` | string | Yes | ISO 8601 datetime with timezone offset |
| `ends_at` | string | Yes | ISO 8601 datetime with timezone offset |
| `title` | string | No | Event title. Defaults to `DEFAULT_TITLE` env var |
| `description` | string | No | Event body / notes. Max 8,000 characters |
| `location` | string | No | Address or meeting URL. Max 1,000 characters |
| `timezone` | string | No | IANA timezone name. Defaults to `DEFAULT_TIMEZONE` env var |
| `attendees` | string[] | No | List of email addresses to invite. Max 20 |

**Successful response — `201 Created`**

```json
{
  "event_id": "abc123xyz",
  "html_link": "https://calendar.google.com/calendar/event?eid=...",
  "title": "Sprint Review",
  "starts_at": "2026-05-01T14:00:00-03:00",
  "ends_at": "2026-05-01T15:00:00-03:00"
}
```

**Error responses**

| Status | `error` field | Cause |
|---|---|---|
| `400` | `bad_request` | Malformed JSON or schema violation |
| `401` | `unauthorized` | `x-api-key` header missing |
| `403` | `forbidden` | `x-api-key` value invalid |
| `422` | `validation_error` | Fails business rules (e.g. event in the past) |
| `429` | `rate_limit_exceeded` | Throttle or daily quota exceeded |
| `500` | `internal_error` | Unexpected Lambda error |
| `502` | `calendar_error` | Google Calendar API rejected the request |

**Example**

```bash
curl -X POST https://<api-id>.execute-api.sa-east-1.amazonaws.com/prod/events \
  -H "x-api-key: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "starts_at": "2026-05-01T14:00:00-03:00",
    "ends_at":   "2026-05-01T15:00:00-03:00",
    "title":     "Sprint Review"
  }'
```

---

## Configuration Parameters

All limits are SAM parameters — pass them at deploy time with `--parameter-overrides` or accept the defaults.

| Parameter | Default | Description |
|---|---|---|
| `DefaultEventTitle` | `Ocupado` | Title used when `title` is not provided |
| `DefaultTimezone` | `America/Sao_Paulo` | Timezone used when `timezone` is not provided |
| `MinDurationMinutes` | `5` | Shortest allowed event duration |
| `MaxDurationHours` | `8` | Longest allowed event duration |
| `MaxFutureDays` | `365` | How far ahead an event can be scheduled |
| `AllowPastEvents` | `false` | Set to `true` to allow past events |
| `ThrottlingBurstLimit` | `5` | Peak concurrent requests before throttling |
| `ThrottlingRateLimit` | `2` | Sustained requests per second before throttling |
| `DailyQuotaLimit` | `100` | Maximum requests per day per API key |
| `GoogleSecretName` | `event-pusher/google-credentials` | Secrets Manager key name |

---

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [uv](https://github.com/astral-sh/uv)
- Python 3.12+
- A Google account with Google Cloud Console access

---

## Setup

### 1. Google Cloud — OAuth2 Credentials

1. Enable the **Google Calendar API** in [Google Cloud Console](https://console.cloud.google.com/)
2. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client IDs**
3. Set application type to **Desktop app** and download the JSON file
4. Run the setup script to generate the refresh token:

```bash
uv run --group dev scripts/setup_google_auth.py
```

The script opens a browser for authorization and prints the `aws` command to store the secret.

### 2. AWS Secrets Manager

Run the command printed by the setup script:

```bash
aws secretsmanager create-secret \
  --name event-pusher/google-credentials \
  --secret-string '{"client_id":"...","client_secret":"...","refresh_token":"..."}'
```

### 3. Build and Deploy

```bash
sam build
sam deploy
```

After a successful deploy, the stack outputs show the API endpoint and API Gateway ID.

### 4. Retrieve Your API Key

```bash
aws apigateway get-api-keys --include-values \
  --query 'items[?name!=`null`].[name,value]' --output table
```

Or find it in the AWS Console under **API Gateway → API Keys**.

---

## Development

```bash
# Install all dependencies
uv sync --all-groups

# Run tests
uv run python -m pytest tests/unit/ -v

# Validate SAM template
sam validate --lint
```
