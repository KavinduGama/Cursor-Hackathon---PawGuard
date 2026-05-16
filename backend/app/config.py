"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AI / voice / search providers
    GEMINI_API_KEY: str = ""
    # Stable Gemini model — override via env if you want 2.0-flash or 2.5-pro.
    GEMINI_MODEL: str = "gemini-2.5-flash"
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_TRIAGE_AGENT_ID: str = ""
    ELEVENLABS_VET_AGENT_ID: str = ""
    ELEVENLABS_FOSTER_AGENT_ID: str = ""
    ELEVENLABS_PHONE_NUMBER_ID: str = ""
    GOOGLE_PLACES_API_KEY: str = ""

    # Mock vet override — when set, /api/location/vets returns a single fake
    # clinic with this phone number (useful for testing the outbound call
    # flow without spamming real vets).
    MOCK_VET_PHONE: str = ""
    MOCK_VET_NAME: str = "PetCare Veterinary Hospital — Nawala"
    MOCK_VET_ADDRESS: str = "47 Nawala Road, Nawala, Sri Lanka"

    # Server
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
