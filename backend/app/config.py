"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AI / voice / search providers
    OPENAI_API_KEY: str = ""
    OPENAI_VISION_MODEL: str = "gpt-4o"
    OPENAI_CLASSIFIER_MODEL: str = "gpt-4o-mini"
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_TRIAGE_AGENT_ID: str = ""
    ELEVENLABS_VET_AGENT_ID: str = ""
    ELEVENLABS_FOSTER_AGENT_ID: str = ""
    ELEVENLABS_PHONE_NUMBER_ID: str = ""
    GOOGLE_PLACES_API_KEY: str = ""

    # Demo call redirect — when set, all outbound calls dial this number
    # instead of the real clinic phone. Google Places still returns real
    # data (names, addresses, ratings) so the UI looks authentic.
    DEMO_CALL_PHONE: str = ""

    # Legacy mock vet override — replaces the entire Places search with a
    # single fake clinic. Prefer DEMO_CALL_PHONE for demos.
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
