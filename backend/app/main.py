"""PawGuard FastAPI application entry point."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import close_db, init_db
from app.routers import auto_dial, calls, location, vision

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="PawGuard AI",
    description="AI animal-rescue assistant — vision, voice, and outbound calls.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vision.router)
app.include_router(location.router)
app.include_router(calls.router)
app.include_router(auto_dial.router)

_req_logger = logging.getLogger("pawguard.requests")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Skip health checks to reduce noise.
    if request.url.path == "/health":
        return await call_next(request)
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    _req_logger.info(
        "%s %s → %s (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "PawGuard AI", "status": "online"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
