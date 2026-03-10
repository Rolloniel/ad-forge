from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CHANNEL = "job_events"


async def notify_step_event(
    session: AsyncSession,
    job_id: str,
    event_type: str,
    step: str | None = None,
    output_preview: str | None = None,
) -> None:
    payload = json.dumps({
        "type": event_type,
        "job_id": job_id,
        "step": step,
        "data": {"output_preview": output_preview} if output_preview else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await session.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": CHANNEL, "payload": payload},
    )


async def listen_job_events(dsn: str) -> AsyncGenerator[dict]:
    conn = await asyncpg.connect(dsn)
    queue: asyncio.Queue[str] = asyncio.Queue()

    def _callback(conn, pid, channel, payload):
        queue.put_nowait(payload)

    await conn.add_listener(CHANNEL, _callback)
    try:
        while True:
            payload = await queue.get()
            yield json.loads(payload)
    finally:
        await conn.remove_listener(CHANNEL, _callback)
        await conn.close()
