from pathlib import Path

import pytest

from us_economy_mcp.config import Settings
from us_economy_mcp.errors import ServiceError
from us_economy_mcp.service import EconomyService, transform_rows


def test_monthly_yoy_transform() -> None:
    rows = [
        {
            "observation_date": f"2025-{month:02d}-01",
            "value": str(100 + month),
            "fetched_at": "2026-01-01T00:00:00+00:00",
        }
        for month in range(1, 13)
    ] + [
        {
            "observation_date": "2026-01-01",
            "value": "111.1",
            "fetched_at": "2026-02-01T00:00:00+00:00",
        }
    ]
    transformed = transform_rows(rows, "monthly", "yoy")
    assert transformed[-1]["value"] == pytest.approx(10.0)


def test_missing_values_remain_missing() -> None:
    rows = [
        {"observation_date": "2025-01-01", "value": "100", "fetched_at": "2026-01-01T00:00:00+00:00"},
        {"observation_date": "2026-01-01", "value": None, "fetched_at": "2026-01-01T00:00:00+00:00"},
    ]
    assert transform_rows(rows, "monthly", "level")[-1]["value"] is None


def test_invalid_transform_for_quarterly() -> None:
    with pytest.raises(ServiceError) as error:
        transform_rows([], "quarterly", "mom")
    assert error.value.code == "unsupported_transform"


def test_daily_yoy_uses_calendar_date() -> None:
    rows = [
        {"observation_date": "2025-01-03", "value": "4", "fetched_at": "2026-01-01T00:00:00+00:00"},
        {"observation_date": "2026-01-02", "value": "5", "fetched_at": "2026-01-02T00:00:00+00:00"},
    ]
    assert transform_rows(rows, "daily", "yoy")[-1]["value"] == pytest.approx(25.0)


@pytest.mark.asyncio
async def test_database_round_trip(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_path=tmp_path / "test.sqlite3",
        refresh_on_start=False,
    )
    service = EconomyService(settings)
    await service.db.connect()
    try:
        await service.db.replace_observations(
            "cpi",
            "fred",
            [{"date": "2026-01-01", "value": "100.5"}],
            "2026-02-01T00:00:00+00:00",
        )
        result = await service.get_latest("cpi")
        assert result["value"] == 100.5
        assert result["observation_date"] == "2026-01-01"
        assert await service.db.last_fetched_at("cpi", "fred") == "2026-02-01T00:00:00+00:00"
    finally:
        await service.db.close()
