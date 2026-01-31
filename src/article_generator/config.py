"""Configuration management for the article generator."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    # API Keys
    anthropic_api_key: str = ""

    # Google Drive settings
    google_credentials_file: Path = Path("credentials.json")
    google_token_file: Path = Path("token.json")
    google_drive_folder_id: str = ""  # Optional: specific folder to save articles

    # Article generation settings
    default_model: str = "claude-sonnet-4-20250514"
    max_research_sources: int = 5
    article_min_words: int = 800
    article_max_words: int = 2000

    # Research settings
    search_results_per_query: int = 5

    # Output settings
    include_sources: bool = True
    include_outline: bool = True

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Config":
        """Load configuration from environment variables."""
        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            load_dotenv()

        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            google_credentials_file=Path(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")),
            google_token_file=Path(os.getenv("GOOGLE_TOKEN_FILE", "token.json")),
            google_drive_folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID", ""),
            default_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            max_research_sources=int(os.getenv("MAX_RESEARCH_SOURCES", "5")),
            article_min_words=int(os.getenv("ARTICLE_MIN_WORDS", "800")),
            article_max_words=int(os.getenv("ARTICLE_MAX_WORDS", "2000")),
        )

    def validate(self) -> list[str]:
        """Validate the configuration and return a list of errors."""
        errors = []

        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required")

        if not self.google_credentials_file.exists():
            errors.append(
                f"Google credentials file not found: {self.google_credentials_file}. "
                "Download it from Google Cloud Console."
            )

        return errors


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
