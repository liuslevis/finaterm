import json
from pathlib import Path

import aiosqlite

from .catalog import INDICATORS


SCHEMA = """
CREATE TABLE IF NOT EXISTS indicators (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_zh TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    preferred_source TEXT NOT NULL,
    frequency TEXT NOT NULL,
    unit TEXT NOT NULL,
    seasonal_adjustment TEXT NOT NULL,
    enabled INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS source_series (
    indicator_id TEXT NOT NULL,
    source TEXT NOT NULL,
    source_series_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    priority INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    PRIMARY KEY (indicator_id, source)
);
CREATE TABLE IF NOT EXISTS observations (
    indicator_id TEXT NOT NULL,
    source TEXT NOT NULL,
    observation_date TEXT NOT NULL,
    value TEXT,
    status TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    raw_json TEXT,
    PRIMARY KEY (indicator_id, source, observation_date)
);
CREATE INDEX IF NOT EXISTS observations_lookup
ON observations(indicator_id, source, observation_date);
CREATE TABLE IF NOT EXISTS refresh_runs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    requested_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    updated_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);
CREATE TABLE IF NOT EXISTS source_status (
    source TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL,
    healthy INTEGER,
    last_attempt_at TEXT,
    last_success_at TEXT,
    last_error_code TEXT
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.executescript(SCHEMA)
        await self._seed_catalog()
        await self.connection.commit()

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()
            self.connection = None

    def _conn(self) -> aiosqlite.Connection:
        if not self.connection:
            raise RuntimeError("Database is not connected")
        return self.connection

    async def _seed_catalog(self) -> None:
        conn = self._conn()
        for item in INDICATORS:
            await conn.execute(
                """
                INSERT INTO indicators VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                  name=excluded.name, name_zh=excluded.name_zh,
                  description=excluded.description, category=excluded.category,
                  preferred_source=excluded.preferred_source,
                  frequency=excluded.frequency, unit=excluded.unit,
                  seasonal_adjustment=excluded.seasonal_adjustment
                """,
                (
                    item.id,
                    item.name,
                    item.name_zh,
                    item.description,
                    item.category,
                    item.source,
                    item.frequency,
                    item.unit,
                    item.seasonal_adjustment,
                ),
            )
            await conn.execute(
                """
                INSERT INTO source_series VALUES (?, ?, ?, ?, 1, '{}')
                ON CONFLICT(indicator_id, source) DO UPDATE SET
                  source_series_id=excluded.source_series_id,
                  source_url=excluded.source_url
                """,
                (
                    item.id,
                    item.source,
                    item.source_series_id,
                    f"https://fred.stlouisfed.org/series/{item.source_series_id}",
                ),
            )

    async def set_source_enabled(self, source: str, enabled: bool) -> None:
        await self._conn().execute(
            """
            INSERT INTO source_status(source, enabled) VALUES (?, ?)
            ON CONFLICT(source) DO UPDATE SET enabled=excluded.enabled
            """,
            (source, int(enabled)),
        )
        await self._conn().commit()

    async def update_source_status(
        self,
        source: str,
        healthy: bool,
        attempted_at: str,
        success_at: str | None = None,
        error_code: str | None = None,
    ) -> None:
        await self._conn().execute(
            """
            INSERT INTO source_status(
              source, enabled, healthy, last_attempt_at, last_success_at, last_error_code
            ) VALUES (?, 1, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
              healthy=excluded.healthy,
              last_attempt_at=excluded.last_attempt_at,
              last_success_at=COALESCE(excluded.last_success_at, source_status.last_success_at),
              last_error_code=excluded.last_error_code
            """,
            (source, int(healthy), attempted_at, success_at, error_code),
        )
        await self._conn().commit()

    async def replace_observations(
        self,
        indicator_id: str,
        source: str,
        observations: list[dict],
        fetched_at: str,
    ) -> int:
        conn = self._conn()
        await conn.execute("BEGIN")
        try:
            await conn.executemany(
                """
                INSERT INTO observations(
                  indicator_id, source, observation_date, value, status, fetched_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_id, source, observation_date) DO UPDATE SET
                  value=excluded.value, status=excluded.status,
                  fetched_at=excluded.fetched_at, raw_json=excluded.raw_json
                """,
                [
                    (
                        indicator_id,
                        source,
                        row["date"],
                        row["value"],
                        "missing" if row["value"] is None else "value",
                        fetched_at,
                        json.dumps(row, separators=(",", ":")),
                    )
                    for row in observations
                ],
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        return len(observations)

    async def get_observations(
        self,
        indicator_id: str,
        source: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 5000,
    ) -> list[dict]:
        conditions = ["indicator_id = ?", "source = ?"]
        params: list[object] = [indicator_id, source]
        if start_date:
            conditions.append("observation_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("observation_date <= ?")
            params.append(end_date)
        params.append(limit)
        cursor = await self._conn().execute(
            f"""
            SELECT observation_date, value, status, fetched_at
            FROM observations
            WHERE {' AND '.join(conditions)}
            ORDER BY observation_date DESC
            LIMIT ?
            """,
            params,
        )
        rows = [dict(row) for row in await cursor.fetchall()]
        rows.reverse()
        return rows

    async def last_fetched_at(self, indicator_id: str, source: str) -> str | None:
        cursor = await self._conn().execute(
            """
            SELECT MAX(fetched_at) AS fetched_at
            FROM observations WHERE indicator_id=? AND source=?
            """,
            (indicator_id, source),
        )
        row = await cursor.fetchone()
        return row["fetched_at"] if row else None

    async def create_refresh_run(self, job_id: str, requested: dict, started_at: str) -> None:
        await self._conn().execute(
            "INSERT INTO refresh_runs(job_id, status, requested_json, started_at) VALUES (?, 'running', ?, ?)",
            (job_id, json.dumps(requested, separators=(",", ":")), started_at),
        )
        await self._conn().commit()

    async def finish_refresh_run(
        self,
        job_id: str,
        status: str,
        finished_at: str,
        updated_count: int,
        errors: list[dict],
    ) -> None:
        await self._conn().execute(
            """
            UPDATE refresh_runs SET status=?, finished_at=?, updated_count=?,
              error_count=?, error_summary=? WHERE job_id=?
            """,
            (
                status,
                finished_at,
                updated_count,
                len(errors),
                json.dumps(errors, separators=(",", ":")) if errors else None,
                job_id,
            ),
        )
        await self._conn().commit()

    async def status(self) -> dict:
        source_cursor = await self._conn().execute(
            "SELECT * FROM source_status ORDER BY source"
        )
        runs_cursor = await self._conn().execute(
            """
            SELECT job_id, status, started_at, finished_at, updated_count,
                   error_count, error_summary
            FROM refresh_runs ORDER BY started_at DESC LIMIT 20
            """
        )
        cache_cursor = await self._conn().execute(
            """
            SELECT COUNT(DISTINCT indicator_id) AS indicator_count,
                   COUNT(*) AS observation_count,
                   MIN(fetched_at) AS oldest_fetched_at,
                   MAX(fetched_at) AS newest_fetched_at
            FROM observations
            """
        )
        cache = dict(await cache_cursor.fetchone())
        return {
            "sources": [dict(row) for row in await source_cursor.fetchall()],
            "jobs": [dict(row) for row in await runs_cursor.fetchall()],
            "cache": cache,
        }
