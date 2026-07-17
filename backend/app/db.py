"""SQLite persistence layer for PawGuard.

Stores vision sessions and call records so they survive backend restarts.
Uses aiosqlite for async access with a single file-based database.

Uses a **single persistent connection** protected by an asyncio.Lock to
avoid "database is locked" errors under concurrent vision + call load.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get("PAWGUARD_DB_PATH", "pawguard.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vision_sessions (
    session_id   TEXT PRIMARY KEY,
    analysis     TEXT NOT NULL DEFAULT '',
    severity     TEXT NOT NULL DEFAULT 'UNKNOWN',
    frame_count  INTEGER NOT NULL DEFAULT 0,
    updated_at   REAL NOT NULL DEFAULT 0,
    created_at   REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS call_records (
    call_id              TEXT PRIMARY KEY,
    agent_type           TEXT NOT NULL,
    conversation_id      TEXT,
    status               TEXT NOT NULL DEFAULT 'initiated',
    summary              TEXT,
    available            INTEGER,   -- 1=true, 0=false, NULL=unknown
    wait_minutes         INTEGER,
    contact_name         TEXT,
    notes                TEXT,
    classified           INTEGER NOT NULL DEFAULT 0,
    -- loop-mode fields
    attempts_json        TEXT,      -- JSON array of CallAttemptSummary dicts
    successful_place_json TEXT,     -- JSON dict of Place
    current_attempt_index INTEGER,
    total_attempts_planned INTEGER,
    created_at           REAL NOT NULL DEFAULT 0,
    updated_at           REAL NOT NULL DEFAULT 0
);
"""

# ── Persistent connection ───────────────────────────────────────────────────

_conn: Optional[aiosqlite.Connection] = None
_lock = asyncio.Lock()


async def init_db() -> None:
    """Create tables if they don't exist and open the persistent connection."""
    global _conn
    _conn = await aiosqlite.connect(_DB_PATH)
    _conn.row_factory = aiosqlite.Row
    await _conn.executescript(_SCHEMA)
    await _conn.commit()
    logger.info("database initialised at %s (persistent connection)", _DB_PATH)


async def close_db() -> None:
    """Close the persistent connection (call during shutdown)."""
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None
        logger.info("database connection closed")


async def _get_conn() -> aiosqlite.Connection:
    """Return the persistent connection, initialising if needed."""
    global _conn
    if _conn is None:
        await init_db()
    return _conn


# ── Vision sessions ─────────────────────────────────────────────────────────

async def upsert_vision_session(
    session_id: str,
    analysis: str,
    severity: str,
    frame_count: int,
    updated_at: float,
    created_at: float,
) -> None:
    async with _lock:
        conn = await _get_conn()
        await conn.execute(
            """
            INSERT INTO vision_sessions
                (session_id, analysis, severity, frame_count, updated_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                analysis = excluded.analysis,
                severity = excluded.severity,
                frame_count = excluded.frame_count,
                updated_at = excluded.updated_at
            """,
            (session_id, analysis, severity, frame_count, updated_at, created_at),
        )
        await conn.commit()


async def load_vision_session(session_id: str) -> Optional[dict[str, Any]]:
    async with _lock:
        conn = await _get_conn()
        cursor = await conn.execute(
            "SELECT * FROM vision_sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_vision_session(session_id: str) -> None:
    async with _lock:
        conn = await _get_conn()
        await conn.execute(
            "DELETE FROM vision_sessions WHERE session_id = ?",
            (session_id,),
        )
        await conn.commit()


# ── Call records ─────────────────────────────────────────────────────────────

def _bool_to_int(v: Optional[bool]) -> Optional[int]:
    if v is None:
        return None
    return 1 if v else 0


def _int_to_bool(v: Optional[int]) -> Optional[bool]:
    if v is None:
        return None
    return bool(v)


async def upsert_call_record(
    call_id: str,
    agent_type: str,
    status: str,
    *,
    conversation_id: Optional[str] = None,
    summary: Optional[str] = None,
    available: Optional[bool] = None,
    wait_minutes: Optional[int] = None,
    contact_name: Optional[str] = None,
    notes: Optional[str] = None,
    classified: bool = False,
    attempts: Optional[list] = None,
    successful_place: Optional[dict] = None,
    current_attempt_index: Optional[int] = None,
    total_attempts_planned: Optional[int] = None,
    created_at: float = 0,
    updated_at: float = 0,
) -> None:
    async with _lock:
        conn = await _get_conn()
        await conn.execute(
            """
            INSERT INTO call_records
                (call_id, agent_type, conversation_id, status,
                 summary, available, wait_minutes, contact_name, notes,
                 classified, attempts_json, successful_place_json,
                 current_attempt_index, total_attempts_planned,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(call_id) DO UPDATE SET
                conversation_id = excluded.conversation_id,
                status = excluded.status,
                summary = excluded.summary,
                available = excluded.available,
                wait_minutes = excluded.wait_minutes,
                contact_name = excluded.contact_name,
                notes = excluded.notes,
                classified = excluded.classified,
                attempts_json = excluded.attempts_json,
                successful_place_json = excluded.successful_place_json,
                current_attempt_index = excluded.current_attempt_index,
                total_attempts_planned = excluded.total_attempts_planned,
                updated_at = excluded.updated_at
            """,
            (
                call_id,
                agent_type,
                conversation_id,
                status,
                summary,
                _bool_to_int(available),
                wait_minutes,
                contact_name,
                notes,
                int(classified),
                json.dumps(attempts) if attempts else None,
                json.dumps(successful_place) if successful_place else None,
                current_attempt_index,
                total_attempts_planned,
                created_at,
                updated_at,
            ),
        )
        await conn.commit()


async def load_call_record(call_id: str) -> Optional[dict[str, Any]]:
    async with _lock:
        conn = await _get_conn()
        cursor = await conn.execute(
            "SELECT * FROM call_records WHERE call_id = ?",
            (call_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["available"] = _int_to_bool(d["available"])
        d["classified"] = bool(d["classified"])
        if d["attempts_json"]:
            d["attempts"] = json.loads(d["attempts_json"])
        else:
            d["attempts"] = []
        if d["successful_place_json"]:
            d["successful_place"] = json.loads(d["successful_place_json"])
        else:
            d["successful_place"] = None
        return d


async def load_all_call_records() -> list[dict[str, Any]]:
    async with _lock:
        conn = await _get_conn()
        cursor = await conn.execute(
            "SELECT * FROM call_records ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["available"] = _int_to_bool(d["available"])
            d["classified"] = bool(d["classified"])
            if d["attempts_json"]:
                d["attempts"] = json.loads(d["attempts_json"])
            else:
                d["attempts"] = []
            if d["successful_place_json"]:
                d["successful_place"] = json.loads(d["successful_place_json"])
            else:
                d["successful_place"] = None
            results.append(d)
        return results
