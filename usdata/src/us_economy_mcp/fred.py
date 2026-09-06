import asyncio
import random
from datetime import UTC, datetime

import httpx

from .errors import ServiceError


class FredClient:
    base_url = "https://api.stlouisfed.org"

    def __init__(self, api_key: str, timeout: float, max_retries: int):
        self.api_key = api_key
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=False,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def fetch_series(self, series_id: str) -> tuple[list[dict], str]:
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": "1940-01-01",
            "sort_order": "asc",
        }
        response: httpx.Response | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.get("/fred/series/observations", params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == self.max_retries:
                    raise ServiceError(
                        "source_unavailable",
                        "FRED request failed",
                        source="fred",
                        retryable=True,
                    ) from exc
                await asyncio.sleep((2**attempt) + random.random())
                continue

            if response.status_code in (401, 403):
                raise ServiceError(
                    "source_authentication_failed",
                    "FRED API authentication failed",
                    source="fred",
                )
            if response.status_code == 429:
                if attempt == self.max_retries:
                    raise ServiceError(
                        "source_rate_limited",
                        "FRED API rate limit exceeded",
                        source="fred",
                        retryable=True,
                    )
                await asyncio.sleep((2**attempt) + random.random())
                continue
            if response.status_code in (502, 503, 504):
                if attempt == self.max_retries:
                    raise ServiceError(
                        "source_unavailable",
                        f"FRED API returned HTTP {response.status_code}",
                        source="fred",
                        retryable=True,
                    )
                await asyncio.sleep((2**attempt) + random.random())
                continue
            if response.is_error:
                try:
                    message = response.json().get("error_message", "FRED request failed")
                except ValueError:
                    message = "FRED request failed"
                code = (
                    "source_authentication_failed"
                    if "api_key" in message.lower()
                    else "source_unavailable"
                )
                raise ServiceError(code, message, source="fred")
            break

        if response is None:
            raise ServiceError("source_unavailable", "FRED request failed", source="fred")
        try:
            payload = response.json()
            raw_observations = payload["observations"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ServiceError(
                "source_unavailable",
                "FRED returned an invalid response",
                source="fred",
            ) from exc
        observations = [
            {"date": row["date"], "value": None if row["value"] == "." else row["value"]}
            for row in raw_observations
        ]
        return observations, datetime.now(UTC).isoformat()

