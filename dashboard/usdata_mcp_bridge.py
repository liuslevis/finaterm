import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


INDICATORS = (
    "fed_funds_rate",
    "treasury_2y",
    "treasury_10y",
    "treasury_10y_2y_spread",
    "nonfarm_payrolls",
    "cpi",
    "ppi_final_demand",
)


async def fetch_series(server_root: str) -> dict:
    start = datetime.now(UTC) - timedelta(days=365 * 20 + 5)
    environment = dict(os.environ)
    environment["REFRESH_ON_START"] = "false"
    environment["MAX_SERIES_POINTS"] = "10000"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "us_economy_mcp"],
        cwd=server_root,
        env=environment,
    )
    output = {}
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call_json(tool: str, arguments: dict | None = None) -> dict:
                result = await session.call_tool(tool, arguments=arguments or {})
                if result.isError or not result.content:
                    raise RuntimeError(f"usdata MCP failed for {tool}")
                return json.loads(result.content[0].text)

            async def read_indicator(indicator_id: str) -> dict:
                return await call_json(
                    "get_series",
                    {
                        "indicator_id": indicator_id,
                        "start_date": start.date().isoformat(),
                        "transform": "level",
                        "limit": 10000,
                    },
                )

            def requires_refresh(indicator_id: str, payload: dict) -> bool:
                if indicator_id != "fed_funds_rate" or not payload.get("ok"):
                    return False
                observations = payload["data"].get("observations", [])
                recent_cutoff = (datetime.now(UTC) - timedelta(days=60)).date().isoformat()
                return sum(row["date"] >= recent_cutoff for row in observations) < 20

            refresh_ids = []
            for indicator_id in INDICATORS:
                payload = await read_indicator(indicator_id)
                if not payload.get("ok"):
                    if payload.get("error", {}).get("code") == "data_unavailable":
                        refresh_ids.append(indicator_id)
                        continue
                    message = payload.get("error", {}).get("message", "unknown error")
                    raise RuntimeError(f"usdata MCP failed for {indicator_id}: {message}")
                if requires_refresh(indicator_id, payload):
                    refresh_ids.append(indicator_id)
                else:
                    output[indicator_id] = payload["data"]

            if refresh_ids:
                refresh = await call_json(
                    "refresh_data",
                    {"indicator_ids": refresh_ids, "force": True},
                )
                if not refresh.get("ok"):
                    message = refresh.get("error", {}).get("message", "unknown error")
                    raise RuntimeError(f"usdata MCP refresh failed: {message}")
                job_id = refresh["job_id"]
                for _ in range(120):
                    status = await call_json("get_refresh_status")
                    job = next(
                        (item for item in status.get("jobs", []) if item["job_id"] == job_id),
                        None,
                    )
                    if job and job["status"] in {"completed", "partial", "failed"}:
                        if job["status"] != "completed":
                            raise RuntimeError(
                                f"usdata MCP refresh {job['status']}: "
                                f"{job.get('error_summary') or 'unknown error'}"
                            )
                        break
                    await asyncio.sleep(0.5)
                else:
                    raise RuntimeError("usdata MCP refresh timed out")

                for indicator_id in refresh_ids:
                    payload = await read_indicator(indicator_id)
                    if not payload.get("ok"):
                        message = payload.get("error", {}).get("message", "unknown error")
                        raise RuntimeError(f"usdata MCP failed for {indicator_id}: {message}")
                    output[indicator_id] = payload["data"]
    return {"provider": "usdata-mcp", "series": output}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read dashboard series from usdata MCP")
    parser.add_argument("--server-root", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(fetch_series(args.server_root)), ensure_ascii=False))
        return 0
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
