from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

BASE_URL = "https://api.heygen.com"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
POLL_INITIAL_DELAY = 5.0
POLL_MAX_DELAY = 60.0
OUTPUTS_DIR = Path("outputs")


class HeyGenClient:
    """Async client for HeyGen avatar video generation."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._api_key = api_key or settings.heygen_api_key
        self._timeout = timeout
        self._max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self._api_key,
            "Content-Type": "application/json",
        }

    async def list_avatars(self) -> list[dict[str, Any]]:
        """List available HeyGen avatars."""
        data = await self._get("/v2/avatars")
        return data.get("data", {}).get("avatars", [])

    async def create_video(
        self,
        *,
        script: str,
        avatar_id: str,
        voice_id: str | None = None,
        background_color: str = "#ffffff",
    ) -> str:
        """Create a video from a script and avatar. Returns the video_id."""
        voice: dict[str, Any] = {"type": "text", "input_text": script}
        if voice_id:
            voice["voice_id"] = voice_id

        payload: dict[str, Any] = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": voice,
                    "background": {
                        "type": "color",
                        "value": background_color,
                    },
                }
            ],
            "dimension": {"width": 1920, "height": 1080},
        }
        data = await self._post("/v2/video/generate", payload)
        return data["data"]["video_id"]

    async def poll_video(self, video_id: str) -> dict[str, Any]:
        """Poll until video is ready and return the result."""
        delay = POLL_INITIAL_DELAY
        while True:
            data = await self._get(f"/v1/video_status.get?video_id={video_id}")
            status = data.get("data", {}).get("status")
            if status == "completed":
                return data["data"]
            if status == "failed":
                raise RuntimeError(
                    f"HeyGen video {video_id} failed: "
                    f"{data.get('data', {}).get('error')}"
                )
            await asyncio.sleep(delay)
            delay = min(delay * 2, POLL_MAX_DELAY)

    async def download_video(
        self, video_url: str, filename: str
    ) -> Path:
        """Download a completed video MP4 to the outputs directory."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        dest = OUTPUTS_DIR / filename
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(video_url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        return dest

    async def _get(self, path: str) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.get(
                        f"{BASE_URL}{path}", headers=self._headers()
                    )
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 500, 502, 503):
                    last_exc = exc
                    await _backoff(attempt)
                    continue
                raise
            except httpx.TransportError as exc:
                last_exc = exc
                await _backoff(attempt)
        raise RuntimeError(
            f"HeyGen request failed after {self._max_retries} retries"
        ) from last_exc

    async def _post(
        self, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{BASE_URL}{path}",
                        headers=self._headers(),
                        json=payload,
                    )
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 500, 502, 503):
                    last_exc = exc
                    await _backoff(attempt)
                    continue
                raise
            except httpx.TransportError as exc:
                last_exc = exc
                await _backoff(attempt)
        raise RuntimeError(
            f"HeyGen request failed after {self._max_retries} retries"
        ) from last_exc


async def _backoff(attempt: int) -> None:
    await asyncio.sleep(min(2**attempt, 30))
