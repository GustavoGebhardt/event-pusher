#!/usr/bin/env python3
"""
Run this locally ONCE to generate the Google OAuth2 refresh token.
Requires: uv run --group dev scripts/setup_google_auth.py

Steps:
  1. Go to Google Cloud Console -> APIs & Services -> Credentials
  2. Create an OAuth 2.0 Client ID (type: Desktop app)
  3. Download the JSON file and pass its path below
  4. Store the printed JSON in Secrets Manager
"""
import json
import subprocess
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Missing dependency. Run: uv run --group dev scripts/setup_google_auth.py")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
SECRET_NAME = "/event-pusher/google-credentials"


def main() -> None:
    print("Google Calendar OAuth2 Setup")
    print("=" * 40)

    credentials_file = input("Path to downloaded OAuth2 credentials JSON: ").strip()

    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
    creds = flow.run_local_server(port=0)

    secret = {
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token,
    }

    secret_json = json.dumps(secret)

    print("\nCredentials generated. Store in SSM Parameter Store with:\n")

    print(
        f"  aws ssm put-parameter \\\n"
        f"    --name \"{SECRET_NAME}\" \\\n"
        f"    --type \"SecureString\" \\\n"
        f"    --value '{secret_json}' \\\n"
        f"    --overwrite"
    )


if __name__ == "__main__":
    main()
