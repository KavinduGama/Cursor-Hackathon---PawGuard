"""PawGuard FastAPI application entry point."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auto_dial, calls, location, vision

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="PawGuard AI",
    description="AI animal-rescue assistant — vision, voice, and outbound calls.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vision.router)
app.include_router(location.router)
app.include_router(calls.router)
app.include_router(auto_dial.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "PawGuard AI", "status": "online"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
