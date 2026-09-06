import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP

from .config import Settings
from .errors import ServiceError
from .service import EconomyService


@dataclass
class AppContext:
    service: EconomyService


settings = Settings()


@asynccontextmanager
async def lifespan(_: FastMCP) -> AsyncIterator[AppContext]:
    service = EconomyService(settings)
    await service.initialize()
    try:
        yield AppContext(service)
    finally:
        await service.close()


mcp = FastMCP(
    "U.S. Economy Data",
    instructions="Query cached U.S. economic indicators and refresh them from official APIs.",
    lifespan=lifespan,
    host=settings.mcp_host,
    port=settings.mcp_port,
)


def _service(ctx: Context) -> EconomyService:
    return ctx.request_context.lifespan_context.service


def _error(exc: ServiceError) -> dict:
    return {"ok": False, "error": exc.to_dict()}


@mcp.tool()
async def list_indicators(
    ctx: Context,
    category: str | None = None,
    source: str | None = None,
    available_only: bool = True,
) -> dict:
    """List supported indicators and metadata."""
    return {
        "ok": True,
        "indicators": _service(ctx).list_indicators(category, source, available_only),
    }


@mcp.tool()
async def get_latest(
    ctx: Context,
    indicator_id: str,
    source: str | None = None,
    transform: str = "level",
) -> dict:
    """Get the latest cached observation for an indicator."""
    try:
        return {"ok": True, "data": await _service(ctx).get_latest(indicator_id, source, transform)}
    except ServiceError as exc:
        return _error(exc)


@mcp.tool()
async def get_series(
    ctx: Context,
    indicator_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    source: str | None = None,
    transform: str = "level",
    limit: int = 500,
) -> dict:
    """Get a cached historical time series."""
    try:
        return {
            "ok": True,
            "data": await _service(ctx).get_series(
                indicator_id, start_date, end_date, source, transform, limit
            ),
        }
    except ServiceError as exc:
        return _error(exc)


@mcp.tool()
async def get_snapshot(ctx: Context, indicator_ids: list[str]) -> dict:
    """Get the latest values of multiple indicators."""
    try:
        return {"ok": True, "items": await _service(ctx).get_snapshot(indicator_ids)}
    except ServiceError as exc:
        return _error(exc)


@mcp.tool()
async def get_release_calendar(
    ctx: Context,
    start_date: str,
    end_date: str,
    importance: str | None = None,
) -> dict:
    """Get economic release dates when a calendar provider is configured."""
    return _error(
        ServiceError(
            "feature_unavailable",
            "No verified release calendar adapter is configured",
            source="fmp",
        )
    )


@mcp.tool()
async def refresh_data(
    ctx: Context,
    indicator_ids: list[str] | None = None,
    source: str | None = None,
    force: bool = False,
) -> dict:
    """Start a background data refresh and return its job ID."""
    service = _service(ctx)
    if not service.settings.enable_manual_refresh:
        return _error(ServiceError("source_disabled", "Manual refresh is disabled"))
    try:
        return {"ok": True, **await service.start_refresh(indicator_ids, source, force)}
    except ServiceError as exc:
        return _error(exc)


@mcp.tool()
async def get_refresh_status(ctx: Context) -> dict:
    """Get data source, cache, and refresh job status."""
    return {"ok": True, **await _service(ctx).db.status()}


@mcp.resource("us-economy://catalog")
async def catalog_resource(ctx: Context) -> str:
    return json.dumps(
        _service(ctx).list_indicators(available_only=False),
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource("us-economy://status")
async def status_resource(ctx: Context) -> str:
    return json.dumps(await _service(ctx).db.status(), ensure_ascii=False, indent=2)


@mcp.resource("us-economy://methodology/{indicator_id}")
async def methodology_resource(indicator_id: str, ctx: Context) -> str:
    try:
        item = _service(ctx)._indicator(indicator_id)
        return json.dumps(item.to_dict(), ensure_ascii=False, indent=2)
    except ServiceError as exc:
        return json.dumps(_error(exc), ensure_ascii=False, indent=2)


def main() -> None:
    transport = settings.mcp_transport
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError("MCP_TRANSPORT must be stdio, sse, or streamable-http")
    mcp.run(transport=transport)

