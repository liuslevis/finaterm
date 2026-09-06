import argparse
from datetime import datetime, timedelta
import json
import mimetypes
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo


mimetypes.add_type("text/javascript", ".js")

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
FINANCE_ROOT = Path(os.getenv("FINANCE_DATA_ROOT", ROOT.parent))
FUTU_ROOT = Path(os.getenv("FUTU_OPEND_ROOT", FINANCE_ROOT / "FutuOpenD"))
USDATA_ROOT = Path(os.getenv("USDATA_ROOT", FINANCE_ROOT / "usdata"))
FUTU_PYTHON = FUTU_ROOT / ".venv" / "Scripts" / "python.exe"
FUTU_KLINE = FUTU_ROOT / "skills" / "futuapi" / "scripts" / "quote" / "get_kline.py"
USDATA_PYTHON = USDATA_ROOT / ".venv" / "Scripts" / "python.exe"
USDATA_BRIDGE = ROOT / "usdata_mcp_bridge.py"
SERVER_ID = "finance-dashboard-uv-v1"
ALLOWED_HOSTS = {
    "query1.finance.yahoo.com",
    "economic-calendar.tradingview.com",
}
DEFAULT_HEADERS = {
    "Accept": "application/json,text/csv,text/plain,*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FinanceDashboard/2.0",
}
CACHE: dict[str, tuple[float, bytes, str]] = {}
CACHE_LOCK = threading.Lock()
FUTU_ASSETS = {
    "btc": ("CC.BTCUSD", "Asia/Shanghai"),
    "qqq": ("US.QQQ", "America/New_York"),
}
FUTU_RANGES = {
    "1d": (timedelta(days=10), "5m"),
    "1mo": (timedelta(days=40), "1d"),
    "6mo": (timedelta(days=190), "1d"),
    "1y": (timedelta(days=370), "1d"),
    "5y": (timedelta(days=365 * 5 + 5), "1d"),
    "10y": (timedelta(days=365 * 10 + 10), "1d"),
    "20y": (timedelta(days=365 * 20 + 20), "1d"),
}


def fetch_upstream(url: str) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Data source is not allowed")

    ttl = 600 if parsed.hostname == "economic-calendar.tradingview.com" else 60
    now = time.monotonic()
    with CACHE_LOCK:
        cached = CACHE.get(url)
        if cached and now - cached[0] < ttl:
            return cached[1], cached[2]

    headers = dict(DEFAULT_HEADERS)
    if parsed.hostname == "economic-calendar.tradingview.com":
        headers["Origin"] = "https://www.tradingview.com"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset()
        if charset:
            content_type = f"{content_type}; charset={charset}"

    with CACHE_LOCK:
        CACHE[url] = (now, body, content_type)
    return body, content_type


def extract_json_object(output: str) -> dict:
    for line in reversed(output.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise RuntimeError("Data source did not return JSON")


def cached_json(key: str, ttl: int, loader) -> bytes:
    now = time.monotonic()
    with CACHE_LOCK:
        cached = CACHE.get(key)
        if cached and now - cached[0] < ttl:
            return cached[1]
    body = json.dumps(loader(), ensure_ascii=False).encode("utf-8")
    with CACHE_LOCK:
        CACHE[key] = (now, body, "application/json; charset=utf-8")
    return body


def fetch_futu(asset_key: str, range_key: str) -> dict:
    if asset_key not in FUTU_ASSETS or range_key not in FUTU_RANGES:
        raise ValueError("Unsupported Futu asset or range")
    if not FUTU_PYTHON.is_file() or not FUTU_KLINE.is_file():
        raise RuntimeError("FutuOpenD client environment is not installed")

    code, timezone_name = FUTU_ASSETS[asset_key]
    duration, ktype = FUTU_RANGES[range_key]
    end = datetime.now()
    start = end - duration
    command = [
        str(FUTU_PYTHON),
        str(FUTU_KLINE),
        code,
        "--ktype",
        ktype,
        "--start",
        start.date().isoformat(),
        "--end",
        end.date().isoformat(),
        "--num",
        "1000",
        "--max-page",
        "5",
        "--json",
    ]
    result = subprocess.run(
        command,
        cwd=FUTU_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )
    payload = extract_json_object(result.stdout)
    if result.returncode or payload.get("error"):
        raise RuntimeError(payload.get("error") or "FutuOpenD request failed")

    timezone = ZoneInfo(timezone_name)
    rows = []
    for row in payload.get("data", []):
        local_time = datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S")
        rows.append(
            {
                "time": int(local_time.replace(tzinfo=timezone).timestamp() * 1000),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("volume"),
            }
        )
    if not rows:
        raise RuntimeError(f"FutuOpenD returned no data for {code}")
    return {"provider": "futu-opend", "asset": asset_key, "code": code, "rows": rows}


def fetch_usdata() -> dict:
    if not USDATA_PYTHON.is_file() or not USDATA_BRIDGE.is_file():
        raise RuntimeError("usdata MCP client environment is not installed")
    result = subprocess.run(
        [
            str(USDATA_PYTHON),
            str(USDATA_BRIDGE),
            "--server-root",
            str(USDATA_ROOT),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )
    payload = extract_json_object(result.stdout)
    if result.returncode or payload.get("error"):
        raise RuntimeError(payload.get("error") or "usdata MCP request failed")
    return payload


class DashboardHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format_string: str, *args: object) -> None:
        return

    def send_body(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        cache_control: str = "no-store",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        request = urllib.parse.urlparse(self.path)
        if request.path == "/__finance_dashboard_health":
            self.send_body(200, SERVER_ID.encode(), "text/plain; charset=utf-8")
            return

        if request.path == "/api/proxy":
            self.handle_proxy(request)
            return

        if request.path == "/api/futu":
            self.handle_futu(request)
            return

        if request.path == "/api/usdata":
            self.handle_usdata()
            return

        if request.path in ("/", "/index.html"):
            if not INDEX.exists():
                self.send_body(404, b"index.html not found", "text/plain; charset=utf-8")
                return
            self.send_body(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            return

        if request.path == "/favicon.ico":
            self.send_body(204, b"", "image/x-icon")
            return

        candidate = (ROOT / request.path.lstrip("/")).resolve()
        if ROOT not in candidate.parents or not candidate.is_file():
            self.send_body(404, b"Not Found", "text/plain; charset=utf-8")
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_body(200, candidate.read_bytes(), content_type)

    def handle_proxy(self, request: urllib.parse.ParseResult) -> None:
        values = urllib.parse.parse_qs(request.query)
        target = (values.get("url") or [""])[0]
        if not target:
            self.send_json_error(400, "Missing url parameter")
            return
        try:
            body, content_type = fetch_upstream(target)
            self.send_body(200, body, content_type)
        except ValueError as error:
            self.send_json_error(403, str(error))
        except urllib.error.HTTPError as error:
            self.send_json_error(502, f"Upstream HTTP {error.code}")
        except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
            self.send_json_error(504, f"Upstream unavailable: {error}")
        except Exception as error:
            self.send_json_error(502, f"Proxy error: {error}")

    def handle_futu(self, request: urllib.parse.ParseResult) -> None:
        values = urllib.parse.parse_qs(request.query)
        asset = (values.get("asset") or [""])[0]
        range_key = (values.get("range") or [""])[0]
        try:
            body = cached_json(
                f"futu:{asset}:{range_key}",
                60,
                lambda: fetch_futu(asset, range_key),
            )
            self.send_body(200, body, "application/json; charset=utf-8")
        except ValueError as error:
            self.send_json_error(400, str(error))
        except subprocess.TimeoutExpired:
            self.send_json_error(504, "FutuOpenD request timed out")
        except Exception as error:
            self.send_json_error(502, f"FutuOpenD unavailable: {error}")

    def handle_usdata(self) -> None:
        try:
            body = cached_json("usdata:mcp:dashboard-series", 600, fetch_usdata)
            self.send_body(200, body, "application/json; charset=utf-8")
        except subprocess.TimeoutExpired:
            self.send_json_error(504, "usdata MCP request timed out")
        except Exception as error:
            self.send_json_error(502, f"usdata MCP unavailable: {error}")

    def send_json_error(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_body(status, body, "application/json; charset=utf-8")


def is_dashboard_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/__finance_dashboard_health", timeout=0.5
        ) as response:
            return response.read().decode() == SERVER_ID
    except Exception:
        return False


def find_or_create_server(start_port: int) -> tuple[ThreadingHTTPServer | None, int]:
    for port in range(start_port, start_port + 21):
        if is_dashboard_running(port):
            return None, port
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
            server.daemon_threads = True
            return server, port
        except OSError:
            continue
    raise RuntimeError("No free local port found in the configured range")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local finance dashboard")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if not INDEX.exists():
        raise SystemExit(f"Missing dashboard file: {INDEX}")

    server, port = find_or_create_server(args.port)
    url = f"http://127.0.0.1:{port}/"
    if not args.no_browser:
        webbrowser.open(url)
    if server is None:
        return 0

    print(f"Finance dashboard: {url}")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
