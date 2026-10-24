"""
One-time helper to obtain GOOGLE_REFRESH_TOKEN for Calendar API.

1. Create OAuth Desktop credentials in Google Cloud Console
2. Enable Google Calendar API
3. Download client secrets JSON, then run:

   python scripts/get_google_refresh_token.py path/to/client_secret.json
"""

from __future__ import annotations

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/get_google_refresh_token.py client_secret.json")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    creds = flow.run_local_server(port=0)
    print("\nAdd these to your .env:\n")
    print(f"GOOGLE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
