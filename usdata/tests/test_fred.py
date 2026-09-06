import httpx
import pytest
import respx

from us_economy_mcp.errors import ServiceError
from us_economy_mcp.fred import FredClient


@pytest.mark.asyncio
@respx.mock
async def test_fetch_series_parses_missing_values() -> None:
    route = respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=httpx.Response(
            200,
            json={
                "observations": [
                    {"date": "2026-01-01", "value": "100.25"},
                    {"date": "2026-02-01", "value": "."},
                ]
            },
        )
    )
    client = FredClient("x" * 32, timeout=1, max_retries=0)
    try:
        rows, fetched_at = await client.fetch_series("CPIAUCSL")
    finally:
        await client.close()
    assert route.called
    assert rows == [
        {"date": "2026-01-01", "value": "100.25"},
        {"date": "2026-02-01", "value": None},
    ]
    assert fetched_at


@pytest.mark.asyncio
@respx.mock
async def test_fetch_series_reports_authentication_failure() -> None:
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=httpx.Response(400, json={"error_message": "Bad api_key"})
    )
    client = FredClient("bad", timeout=1, max_retries=0)
    try:
        with pytest.raises(ServiceError) as error:
            await client.fetch_series("CPIAUCSL")
    finally:
        await client.close()
    assert error.value.code == "source_authentication_failed"

