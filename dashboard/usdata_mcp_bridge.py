import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


INDICATORS = (
    "treasury_10y_2y_spread",
    "nonfarm_payrolls",
    "cpi",
    "ppi_final_demand",
)


async def fetch_series(server_root: str) -> dict:
    start = datetime.now(UTC) - timedelta(days=365 * 12 + 4)
    environment = dict(os.environ)
    environment["REFRESH_ON_START"] = "false"
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
            for indicator_id in INDICATORS:
                result = await session.call_tool(
                    "get_series",
                    arguments={
                        "indicator_id": indicator_id,
                        "start_date": start.date().isoformat(),
                        "transform": "level",
                        "limit": 5000,
                    },
                )
                if result.isError or not result.content:
                    raise RuntimeError(f"usdata MCP failed for {indicator_id}")
                payload = json.loads(result.content[0].text)
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
