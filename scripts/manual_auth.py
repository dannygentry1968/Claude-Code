#!/usr/bin/env python3
"""Manual Google OAuth authentication for headless environments."""

import json
from pathlib import Path

from google_auth_oauthlib.flow import Flow

# Scopes required for Google Docs and Drive
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

def main():
    credentials_file = Path("credentials/credentials.json")
    token_file = Path("credentials/token.json")

    if not credentials_file.exists():
        print(f"ERROR: Credentials file not found: {credentials_file}")
        print("Please add your Google OAuth credentials first.")
        return

    # Create the flow using the client secrets file
    flow = Flow.from_client_secrets_file(
        str(credentials_file),
        scopes=SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob"  # Manual copy/paste flow
    )

    # Generate the authorization URL
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    print("\n" + "=" * 60)
    print("GOOGLE AUTHENTICATION")
    print("=" * 60)
    print("\n1. Open this URL in your browser:\n")
    print(auth_url)
    print("\n2. Sign in with your Google account")
    print("3. Click 'Allow' to grant permissions")
    print("4. Copy the authorization code shown on the page")
    print("\n" + "=" * 60)

    # Get the authorization code from user
    code = input("\nPaste the authorization code here: ").strip()

    if not code:
        print("ERROR: No code provided. Exiting.")
        return

    try:
        # Exchange the authorization code for credentials
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Save the credentials
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        with open(token_file, "w") as f:
            json.dump(token_data, f, indent=2)

        print(f"\nSUCCESS! Token saved to {token_file}")
        print("You can now use the article generator!")

    except Exception as e:
        print(f"\nERROR: Failed to authenticate: {e}")
        print("Please try again.")


if __name__ == "__main__":
    main()
