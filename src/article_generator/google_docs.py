"""Google Docs and Drive integration for saving articles."""

import json
from dataclasses import dataclass
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes required for creating and writing Google Docs
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


@dataclass
class GoogleDocResult:
    """Result of creating a Google Doc."""

    doc_id: str
    doc_url: str
    title: str


class GoogleDocsClient:
    """Client for interacting with Google Docs and Drive APIs."""

    def __init__(
        self,
        credentials_file: Path,
        token_file: Path,
        folder_id: str | None = None,
    ):
        """Initialize the Google Docs client.

        Args:
            credentials_file: Path to the OAuth2 credentials JSON file.
            token_file: Path to store/load the user's access token.
            folder_id: Optional Google Drive folder ID to save documents to.
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.folder_id = folder_id
        self._creds: Credentials | None = None
        self._docs_service = None
        self._drive_service = None

    def authenticate(self) -> None:
        """Authenticate with Google APIs.

        This will open a browser window for OAuth2 authentication if needed.
        """
        creds = None

        # Load existing token if available
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)

        # Refresh or get new credentials if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    raise FileNotFoundError(
                        f"Google credentials file not found: {self.credentials_file}\n"
                        "Please download OAuth2 credentials from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        self._creds = creds
        self._docs_service = build("docs", "v1", credentials=creds)
        self._drive_service = build("drive", "v3", credentials=creds)

    def create_document(self, title: str, content: str) -> GoogleDocResult:
        """Create a new Google Doc with the given title and content.

        Args:
            title: The document title.
            content: The document content in plain text (supports basic formatting).

        Returns:
            GoogleDocResult with the document ID, URL, and title.

        Raises:
            RuntimeError: If not authenticated.
            HttpError: If the API request fails.
        """
        if not self._docs_service or not self._drive_service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            # Create the document
            doc = self._docs_service.documents().create(body={"title": title}).execute()
            doc_id = doc.get("documentId")

            # Insert content into the document
            requests = self._build_content_requests(content)
            if requests:
                self._docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests}
                ).execute()

            # Move to folder if specified
            if self.folder_id:
                self._move_to_folder(doc_id, self.folder_id)

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

            return GoogleDocResult(doc_id=doc_id, doc_url=doc_url, title=title)

        except HttpError as error:
            raise RuntimeError(f"Failed to create Google Doc: {error}")

    def _build_content_requests(self, content: str) -> list[dict]:
        """Build Google Docs API requests for inserting content.

        This handles basic markdown-style formatting:
        - # Heading 1, ## Heading 2, ### Heading 3
        - **bold** and *italic*
        - Paragraphs separated by blank lines
        """
        if not content.strip():
            return []

        requests = []
        lines = content.split("\n")
        current_index = 1  # Google Docs index starts at 1

        for line in lines:
            if not line and current_index > 1:
                # Empty line - add paragraph break
                requests.append(
                    {"insertText": {"location": {"index": current_index}, "text": "\n"}}
                )
                current_index += 1
                continue

            # Determine heading level
            heading_style = None
            text = line

            if line.startswith("### "):
                heading_style = "HEADING_3"
                text = line[4:]
            elif line.startswith("## "):
                heading_style = "HEADING_2"
                text = line[3:]
            elif line.startswith("# "):
                heading_style = "HEADING_1"
                text = line[2:]

            # Insert the text
            text_with_newline = text + "\n"
            requests.append(
                {
                    "insertText": {
                        "location": {"index": current_index},
                        "text": text_with_newline,
                    }
                }
            )

            # Apply heading style if needed
            if heading_style:
                requests.append(
                    {
                        "updateParagraphStyle": {
                            "range": {
                                "startIndex": current_index,
                                "endIndex": current_index + len(text_with_newline),
                            },
                            "paragraphStyle": {"namedStyleType": heading_style},
                            "fields": "namedStyleType",
                        }
                    }
                )

            current_index += len(text_with_newline)

        return requests

    def _move_to_folder(self, file_id: str, folder_id: str) -> None:
        """Move a file to a specific Drive folder."""
        # Get current parents
        file = (
            self._drive_service.files().get(fileId=file_id, fields="parents").execute()
        )
        previous_parents = ",".join(file.get("parents", []))

        # Move to new folder
        self._drive_service.files().update(
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()

    def list_recent_documents(self, limit: int = 10) -> list[dict]:
        """List recent documents created by this application.

        Args:
            limit: Maximum number of documents to return.

        Returns:
            List of document metadata dictionaries.
        """
        if not self._drive_service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        results = (
            self._drive_service.files()
            .list(
                pageSize=limit,
                fields="files(id, name, createdTime, webViewLink)",
                q="mimeType='application/vnd.google-apps.document'",
                orderBy="createdTime desc",
            )
            .execute()
        )

        return results.get("files", [])
