from __future__ import annotations

import asyncio

job_queue: asyncio.Queue[str] = asyncio.Queue()
