"""Configuration management for ByteVoice via Pydantic-Settings.

Reads configuration from environment variables and .env.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Runtime application settings."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ENV, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(default="", alias="DATABASE_URL")

    # ElevenLabs Voice Agent
    elevenlabs_api_key: SecretStr = Field(default=SecretStr(""), alias="ELEVENLABS_API_KEY")
    elevenlabs_agent_id: str = Field(default="", alias="ELEVENLABS_AGENT_ID")
    elevenlabs_voice_id: str = Field(default="", alias="ELEVENLABS_VOICE_ID")

    # Server Ports
    api_port: int = Field(default=8000, alias="PORT")
    web_dir: str = Field(default="", alias="BYTEVOICE_WEB_DIR")

    @property
    def has_voice(self) -> bool:
        """Whether ElevenLabs credentials are configured."""
        return bool(self.elevenlabs_api_key.get_secret_value() and self.elevenlabs_agent_id)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide cached settings."""
    return Settings()

