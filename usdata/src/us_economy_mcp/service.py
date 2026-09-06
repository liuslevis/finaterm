import asyncio
import math
import uuid
from bisect import bisect_right
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from .catalog import INDICATOR_BY_ID, INDICATORS, Indicator
from .config import Settings
from .db import Database
from .errors import ServiceError
from .fred import FredClient


def utc_now() -> datetime:
    return datetime.now(UTC)


def _lag_for(frequency: str, transform: str) -> int:
    lags = {
        "monthly": {"mom": 1, "qoq": 3, "yoy": 12},
        "quarterly": {"qoq": 1, "annualized_qoq": 1, "yoy": 4},
        "weekly": {"yoy": 52},
    }
    try:
        return lags[frequency][transform]
    except KeyError as exc:
        raise ServiceError(
            "unsupported_transform",
            f"{transform} is not supported for {frequency} data",
        ) from exc


def transform_rows(rows: list[dict], frequency: str, transform: str) -> list[dict]:
    if transform == "level":
        return [{**row, "value": float(row["value"]) if row["value"] is not None else None} for row in rows]

    if frequency == "daily" and transform == "yoy":
        dates = [date.fromisoformat(row["observation_date"]) for row in rows]
        output: list[dict] = []
        for index, row in enumerate(rows):
            current_date = dates[index]
            try:
                target = current_date.replace(year=current_date.year - 1)
            except ValueError:
                target = current_date.replace(year=current_date.year - 1, day=28)
            insertion = bisect_right(dates, target, hi=index)
            candidates = [
                candidate
                for candidate in (insertion - 1, insertion)
                if 0 <= candidate < index
            ]
            previous_index = min(
                candidates,
                key=lambda candidate: abs(dates[candidate] - target),
                default=-1,
            )
            value = None
            if (
                row["value"] is not None
                and previous_index >= 0
                and abs(target - dates[previous_index]) <= timedelta(days=7)
                and rows[previous_index]["value"] is not None
            ):
                current = Decimal(row["value"])
                previous = Decimal(rows[previous_index]["value"])
                if previous != 0:
                    value = float((current / previous - 1) * 100)
            output.append({**row, "value": value})
        return output

    lag = _lag_for(frequency, transform)
    output: list[dict] = []
    for index, row in enumerate(rows):
        value = None
        if row["value"] is not None and index >= lag and rows[index - lag]["value"] is not None:
            try:
                current = Decimal(row["value"])
                previous = Decimal(rows[index - lag]["value"])
                if previous != 0:
                    ratio = current / previous
                    if transform == "annualized_qoq":
                        value = (float(ratio) ** 4 - 1) * 100
                    else:
                        value = float((ratio - 1) * 100)
            except (InvalidOperation, ValueError, OverflowError):
                value = None
        output.append({**row, "value": value})
    return output


class EconomyService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.database_path)
        self.fred: FredClient | None = None
        self._refresh_tasks: dict[str, asyncio.Task] = {}
        self._scheduler_task: asyncio.Task | None = None
        self._stopping = asyncio.Event()
        self._semaphore = asyncio.Semaphore(settings.source_concurrency)
        self._db_write_lock = asyncio.Lock()

    async def initialize(self) -> None:
        await self.db.connect()
        source_keys = {
            "fred": self.settings.fred_api_key,
            "bea": self.settings.bea_api_key,
            "census": self.settings.census_api_key,
            "fmp": self.settings.fmp_api_key,
        }
        for source, key in source_keys.items():
            await self.db.set_source_enabled(source, bool(key))
        if self.settings.fred_api_key:
            self.fred = FredClient(
                self.settings.fred_api_key,
                self.settings.http_timeout_seconds,
                self.settings.max_retries,
            )
        self._scheduler_task = asyncio.create_task(self._scheduler(), name="daily-refresh")
        if self.settings.refresh_on_start and self.fred:
            await self.start_refresh(force=False)

    async def close(self) -> None:
        self._stopping.set()
        if self._scheduler_task:
            self._scheduler_task.cancel()
        for task in self._refresh_tasks.values():
            task.cancel()
        tasks = [task for task in [self._scheduler_task, *self._refresh_tasks.values()] if task]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self.fred:
            await self.fred.close()
        await self.db.close()

    def list_indicators(
        self,
        category: str | None = None,
        source: str | None = None,
        available_only: bool = True,
    ) -> list[dict]:
        return [
            item.to_dict()
            for item in INDICATORS
            if (category is None or item.category == category)
            and (source is None or item.source == source)
            and (not available_only or item.status == "available")
        ]

    def _indicator(self, indicator_id: str) -> Indicator:
        try:
            return INDICATOR_BY_ID[indicator_id]
        except KeyError as exc:
            raise ServiceError(
                "indicator_not_found",
                f"Unknown indicator: {indicator_id}",
            ) from exc

    async def get_series(
        self,
        indicator_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        source: str | None = None,
        transform: str = "level",
        limit: int = 500,
    ) -> dict:
        item = self._indicator(indicator_id)
        selected_source = source or item.source
        if selected_source != item.source:
            raise ServiceError(
                "source_disabled",
                f"{indicator_id} is not available from {selected_source}",
                source=selected_source,
            )
        if limit < 1 or limit > self.settings.max_series_points:
            raise ServiceError(
                "invalid_request",
                f"limit must be between 1 and {self.settings.max_series_points}",
            )
        for value in (start_date, end_date):
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError as exc:
                    raise ServiceError("invalid_request", f"Invalid ISO date: {value}") from exc
        if start_date and end_date and start_date > end_date:
            raise ServiceError("invalid_request", "start_date must not be after end_date")

        rows = await self.db.get_observations(
            item.id, selected_source, start_date, end_date, limit
        )
        if not rows:
            raise ServiceError(
                "data_unavailable",
                f"No cached data is available for {indicator_id}",
                source=selected_source,
                retryable=True,
            )
        transformed = transform_rows(rows, item.frequency, transform)
        fetched_at = max(row["fetched_at"] for row in rows)
        stale = utc_now() - datetime.fromisoformat(fetched_at) > timedelta(
            hours=self.settings.cache_ttl_hours
        )
        return {
            "indicator_id": item.id,
            "name": item.name,
            "unit": "percent_change" if transform != "level" else item.unit,
            "frequency": item.frequency,
            "transform": transform,
            "source": selected_source,
            "source_series_id": item.source_series_id,
            "fetched_at": fetched_at,
            "is_stale": stale,
            "observations": [
                {"date": row["observation_date"], "value": row["value"]}
                for row in transformed
            ],
        }

    async def get_latest(
        self,
        indicator_id: str,
        source: str | None = None,
        transform: str = "level",
    ) -> dict:
        item = self._indicator(indicator_id)
        required = 400 if item.frequency == "daily" else 60
        series = await self.get_series(
            indicator_id,
            source=source,
            transform=transform,
            limit=required,
        )
        available = [row for row in series["observations"] if row["value"] is not None]
        if not available:
            raise ServiceError(
                "data_unavailable",
                f"No usable value is available for {indicator_id}",
                source=series["source"],
            )
        latest = available[-1]
        return {
            key: series[key]
            for key in (
                "indicator_id",
                "name",
                "unit",
                "transform",
                "source",
                "source_series_id",
                "fetched_at",
                "is_stale",
            )
        } | {
            "value": latest["value"],
            "observation_date": latest["date"],
        }

    async def get_snapshot(self, indicator_ids: list[str]) -> list[dict]:
        if not indicator_ids or len(indicator_ids) > 50:
            raise ServiceError(
                "invalid_request",
                "indicator_ids must contain between 1 and 50 items",
            )

        async def one(indicator_id: str) -> dict:
            try:
                return {"status": "ok", "data": await self.get_latest(indicator_id)}
            except ServiceError as exc:
                return {"status": "error", "indicator_id": indicator_id, "error": exc.to_dict()}

        return await asyncio.gather(*(one(indicator_id) for indicator_id in indicator_ids))

    async def start_refresh(
        self,
        indicator_ids: list[str] | None = None,
        source: str | None = None,
        force: bool = False,
    ) -> dict:
        if source and source != "fred":
            raise ServiceError(
                "source_disabled",
                f"No data adapter is implemented for {source}",
                source=source,
            )
        if not self.fred:
            raise ServiceError(
                "source_disabled",
                "FRED_API_KEY or FED_API is not configured",
                source="fred",
            )
        selected = indicator_ids or [item.id for item in INDICATORS]
        unknown = [indicator_id for indicator_id in selected if indicator_id not in INDICATOR_BY_ID]
        if unknown:
            raise ServiceError(
                "indicator_not_found",
                f"Unknown indicators: {', '.join(unknown)}",
            )
        signature = ",".join(sorted(selected))
        for job_id, task in self._refresh_tasks.items():
            if not task.done() and task.get_name() == signature:
                return {"job_id": job_id, "status": "already_running"}

        job_id = str(uuid.uuid4())
        requested = {"indicator_ids": selected, "source": "fred", "force": force}
        await self.db.create_refresh_run(job_id, requested, utc_now().isoformat())
        task = asyncio.create_task(
            self._run_refresh(job_id, selected, force),
            name=signature,
        )
        self._refresh_tasks[job_id] = task
        task.add_done_callback(lambda _: self._refresh_tasks.pop(job_id, None))
        return {"job_id": job_id, "status": "running"}

    async def _run_refresh(
        self,
        job_id: str,
        indicator_ids: list[str],
        force: bool,
    ) -> None:
        errors: list[dict] = []
        counts = await asyncio.gather(
            *(self._refresh_one(INDICATOR_BY_ID[item], force) for item in indicator_ids),
            return_exceptions=True,
        )
        updated_count = 0
        for indicator_id, result in zip(indicator_ids, counts, strict=True):
            if isinstance(result, BaseException):
                error = result.to_dict() if isinstance(result, ServiceError) else {
                    "code": "source_unavailable",
                    "message": type(result).__name__,
                    "source": "fred",
                    "retryable": False,
                    "details": None,
                }
                errors.append({"indicator_id": indicator_id, **error})
            else:
                updated_count += result
        status = "completed" if not errors else ("failed" if not updated_count else "partial")
        await self.db.finish_refresh_run(
            job_id,
            status,
            utc_now().isoformat(),
            updated_count,
            errors,
        )

    async def _refresh_one(self, item: Indicator, force: bool) -> int:
        if not self.fred:
            raise ServiceError("source_disabled", "FRED is disabled", source="fred")
        if not force:
            last_fetched_at = await self.db.last_fetched_at(item.id, "fred")
            if last_fetched_at and utc_now() - datetime.fromisoformat(
                last_fetched_at
            ) <= timedelta(hours=self.settings.cache_ttl_hours):
                return 0
        async with self._semaphore:
            attempted_at = utc_now().isoformat()
            try:
                observations, fetched_at = await self.fred.fetch_series(item.source_series_id)
                async with self._db_write_lock:
                    count = await self.db.replace_observations(
                        item.id, "fred", observations, fetched_at
                    )
                    await self.db.update_source_status(
                        "fred", True, attempted_at, success_at=fetched_at
                    )
                return count
            except ServiceError as exc:
                async with self._db_write_lock:
                    await self.db.update_source_status(
                        "fred", False, attempted_at, error_code=exc.code
                    )
                raise

    async def _scheduler(self) -> None:
        zone = ZoneInfo(self.settings.refresh_timezone)
        try:
            hour_text, minute_text = self.settings.refresh_time.split(":", maxsplit=1)
            hour, minute = int(hour_text), int(minute_text)
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError
        except ValueError as exc:
            raise RuntimeError("REFRESH_TIME must use HH:MM in 24-hour format") from exc

        while not self._stopping.is_set():
            now = datetime.now(zone)
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            seconds = max(1, math.ceil((next_run - now).total_seconds()))
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=seconds)
            except TimeoutError:
                if self.fred:
                    await self.start_refresh()
