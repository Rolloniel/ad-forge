from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

BASE_URL = "https://queue.fal.run"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
POLL_INITIAL_DELAY = 2.0
POLL_MAX_DELAY = 30.0
OUTPUTS_DIR = Path("outputs")


class FalClient:
    """Async client for FAL.ai image and video generation."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._api_key = api_key or settings.fal_key
        self._timeout = timeout
        self._max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Key {self._api_key}",
            "Content-Type": "application/json",
        }

    async def generate_image(
        self,
        prompt: str,
        *,
        image_size: str = "landscape_16_9",
        num_images: int = 1,
    ) -> dict[str, Any]:
        """Submit a Flux Pro image generation job and poll until complete."""
        payload: dict[str, Any] = {
            "prompt": prompt,
            "image_size": image_size,
            "num_images": num_images,
        }
        return await self._submit_and_poll(
            "fal-ai/flux-pro/v1.1", payload
        )

    async def generate_video(
        self,
        prompt: str,
        *,
        image_url: str | None = None,
        duration: str = "5",
        aspect_ratio: str = "16:9",
    ) -> dict[str, Any]:
        """Submit a Kling video generation job and poll until complete."""
        payload: dict[str, Any] = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }
        if image_url:
            payload["image_url"] = image_url
        return await self._submit_and_poll(
            "fal-ai/kling-video/v1.5/pro", payload
        )

    async def download_file(
        self, url: str, filename: str
    ) -> Path:
        """Download an output file from a FAL result URL."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        dest = OUTPUTS_DIR / filename
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        return dest

    async def _submit_and_poll(
        self, model: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Submit a job and poll for the result with exponential backoff."""
        submit_data = await self._post(f"/{model}", payload)
        request_id = submit_data["request_id"]
        status_url = submit_data.get(
            "status_url",
            f"{BASE_URL}/{model}/requests/{request_id}/status",
        )
        result_url = submit_data.get(
            "response_url",
            f"{BASE_URL}/{model}/requests/{request_id}",
        )

        delay = POLL_INITIAL_DELAY
        while True:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    status_url, headers=self._headers()
                )
                resp.raise_for_status()
                status = resp.json()

            if status.get("status") == "COMPLETED":
                # Prefer response_url from status response if available
                final_url = status.get("response_url", result_url)
                return await self._get_result(final_url)
            if status.get("status") == "FAILED":
                raise RuntimeError(
                    f"FAL job {request_id} failed: {status.get('error')}"
                )
            await asyncio.sleep(delay)
            delay = min(delay * 2, POLL_MAX_DELAY)

    async def _get_result(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

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
            f"FAL request failed after {self._max_retries} retries"
        ) from last_exc


async def _backoff(attempt: int) -> None:
    await asyncio.sleep(min(2**attempt, 30))
