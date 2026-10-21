"""端到端 HTTP 冒烟测试：起真实 server.py，打一圈接口，校验结构与一致性。

同时验证 Parquet 数据集与「未转换交易日回退 7z」两条路径在 HTTP 层都正常。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
PY = sys.executable
PORT = int(os.environ.get("HFQ_TEST_PORT", "8791"))
BASE = f"http://127.0.0.1:{PORT}"


def get(path, timeout=120):
    t0 = time.perf_counter()
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        body = json.loads(r.read().decode("utf-8"))
    return body, time.perf_counter() - t0


def main():
    env = dict(os.environ, HFQ_PORT=str(PORT), PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen([PY, "server.py"], cwd=HFQ, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    try:
        for _ in range(80):
            try:
                get("/api/health", timeout=3)
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.25)
        else:
            raise SystemExit("服务未启动")

        checks = []

        def check(label, path, fn=None):
            try:
                body, dt = get(path)
            except urllib.error.HTTPError as e:
                checks.append((label, False, f"HTTP {e.code}", 0.0))
                print(f"  [FAIL] {label:<34} HTTP {e.code}")
                return None
            ok, note = True, ""
            if fn:
                ok, note = fn(body)
            checks.append((label, ok, note, dt))
            print(f"  [{'OK  ' if ok else 'FAIL'}] {label:<34} {dt*1000:8.1f} ms  {note}")
            return body

        h = check("health", "/api/health",
                  lambda b: (b.get("status") == "ok", f"dates={len(b.get('dates', []))}"))
        check("dates", "/api/dates", lambda b: (len(b["dates"]) > 0, f"{len(b['dates'])} 天"))
        check("stocks(20260901)", "/api/stocks?date=20260901",
              lambda b: (b["total"] > 7000, f"{b['total']} 只"))

        # Parquet 覆盖的交易日
        for date in ("20260901", "20260630"):
            check(f"basic {date}/000001.SZ", f"/api/basic?code=000001.SZ&date={date}",
                  lambda b: (b.get("last", 0) > 0,
                             f"last={b.get('last')} 涨幅={b.get('change_pct'):.2f}%"))
            check(f"events {date}/000001.SZ", f"/api/events?code=000001.SZ&date={date}&limit=50",
                  lambda b: (b["total"] > 1000 and len(b["events"]) == 50,
                             f"total={b['total']}"))
            check(f"ordermap {date}/000001.SZ", f"/api/ordermap?code=000001.SZ&date={date}",
                  lambda b: (len(b["buy"]) > 0 and len(b["sell"]) > 0,
                             f"买{len(b['buy'])} 卖{len(b['sell'])}"))
            check(f"books {date}/000001.SZ", f"/api/books?code=000001.SZ&date={date}",
                  lambda b: (len(b["t"]) > 100, f"{len(b['t'])} 帧"))
            check(f"intraday {date}/000001.SZ", f"/api/intraday?code=000001.SZ&date={date}",
                  lambda b: (len(b["points"]) > 100, f"{len(b['points'])} 点"))
            check(f"orders {date}/000001.SZ", f"/api/orders?code=000001.SZ&date={date}",
                  lambda b: (b["total"] > 100, f"total={b['total']}"))

        # 另一个已转换交易日（早期靠 7z，现走 Parquet）
        check("events 20260918", "/api/events?code=000001.SZ&date=20260918&limit=20",
              lambda b: (b["total"] > 1000, f"total={b['total']}"))
        check("basic 20260918", "/api/basic?code=000001.SZ&date=20260918",
              lambda b: (b.get("last", 0) > 0, f"last={b.get('last')}"))

        # 哨兵股票：旧实现 500，新实现必须正常
        r = check("basic 20260731/001267.SZ(哨兵)", "/api/basic?code=001267.SZ&date=20260731",
                  lambda b: (b.get("last", 0) > 0, f"last={b.get('last')}"))
        check("events 20260731/001267.SZ(哨兵)",
              "/api/events?code=001267.SZ&date=20260731&limit=20",
              lambda b: (b["total"] > 1000, f"total={b['total']}"))

        check("daily 000001.SZ", "/api/daily?code=000001.SZ",
              lambda b: (len(b["days"]) > 50, f"{len(b['days'])} 天"))
        check("region 20260901/000001.SZ",
              "/api/region?code=000001.SZ&date=20260901&start=093000&end=150000",
              lambda b: (b.get("found") is True, f"count={b.get('count')}"))
        check("track 20260901/000001.SZ",
              "/api/track?code=000001.SZ&date=20260901&order_id=1",
              lambda b: (b.get("found") in (True, False), f"found={b.get('found')}"))

        ok_n = sum(1 for c in checks if c[1])
        print(f"\n=== HTTP 冒烟 ===  OK {ok_n}/{len(checks)}")
        bad = [c for c in checks if not c[1]]
        for b in bad:
            print(f"  ! {b[0]}: {b[2]}")
        out = os.path.join(HFQ, "snapshot", "http_smoke.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump([{"label": c[0], "ok": c[1], "note": c[2],
                        "ms": round(c[3] * 1000, 2)} for c in checks],
                      fh, indent=2, ensure_ascii=False)
        print(f"明细 -> {out}")
        return 0 if not bad else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
