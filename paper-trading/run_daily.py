"""模拟盘每日任务（幂等，可反复运行）。dashboard 启动后每 2 小时自动调用一次。

    uv run --project paper-trading python paper-trading/run_daily.py [--git]

--git：运行前 fetch + fast-forward 拉取其他电脑的结果；运行后只提交 paper-trading/state 并 push。
任何 git 步骤失败都只记日志、不影响记账。
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine import STATE, run_strategy  # noqa: E402
from market import CACHE, Market  # noqa: E402
from strategies import STRATEGIES  # noqa: E402

BENCHMARKS = {"SHY": "2Y国债 (SHY)", "sh000300": "沪深300", "QQQ": "QQQ", "SPY": "标普500 (SPY)"}
HISTORY_START = "2009-06-01"


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=120)


def git_pull() -> None:
    if git("fetch", "--quiet").returncode:
        log("git fetch 失败，跳过同步")
        return
    r = git("merge", "--ff-only", "--quiet", "@{u}")
    log("git 已快进到远端" if r.returncode == 0 else f"git 无法快进（本地有未推送提交或冲突），沿用本地状态：{r.stderr.strip()[:200]}")


def git_push(summary: str) -> None:
    if not git("status", "--porcelain", "--", "state").stdout.strip():
        log("state 无变化，不提交")
        return
    git("add", "--", "state")
    r = git("commit", "--quiet", "-m", f"paper-trading: {summary}", "--", "state")
    if r.returncode:
        log(f"git commit 失败：{r.stderr.strip()[:200]}")
        return
    r = git("push", "--quiet")
    log("git push 完成" if r.returncode == 0 else f"git push 失败（下次运行重试）：{r.stderr.strip()[:200]}")


def update_benchmarks(market: Market, start: str) -> int:
    """长表 date,symbol,close，只追加未记录过的 (date, symbol)。"""
    path = STATE / "benchmarks.csv"
    seen = set()
    if path.exists():
        with path.open(encoding="utf-8") as f:
            seen = {(r["date"], r["symbol"]) for r in csv.DictReader(f)}
    base = (pd.Timestamp(start) - pd.Timedelta(days=10))
    rows = []
    for sym in BENCHMARKS:
        s = market[sym].Close
        for d, v in s[s.index >= base].items():
            key = (d.date().isoformat(), sym)
            if key not in seen and pd.notna(v):
                rows.append({"date": key[0], "symbol": sym, "close": round(float(v), 4)})
    rows.sort(key=lambda r: (r["date"], r["symbol"]))
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "symbol", "close"], lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def write_if_changed(path: Path, data) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--git", action="store_true")
    args = ap.parse_args()
    CACHE.mkdir(exist_ok=True)
    STATE.mkdir(exist_ok=True)
    status = {"started_at": datetime.now().isoformat(timespec="seconds"), "ok": False, "strategies": {}}
    try:
        if args.git:
            git_pull()
        symbols = sorted({s for st in STRATEGIES for s in st.DATA} | set(BENCHMARKS))
        bench_start = (pd.Timestamp(min(st.START for st in STRATEGIES)) - pd.Timedelta(days=30)).date().isoformat()
        market = Market(symbols, HISTORY_START, need_gpr=any(st.NEED_GPR for st in STRATEGIES), cn_start=bench_start)
        parts = []
        for st in STRATEGIES:
            n = run_strategy(st, market)
            acct = json.loads((STATE / st.ID / "account.json").read_text()) if (STATE / st.ID / "account.json").exists() else {}
            status["strategies"][st.ID] = {"new_days": n, "last_date": acct.get("last_date"), "nav": acct.get("nav")}
            log(f"{st.ID}: 新增 {n} 天，截至 {acct.get('last_date')}，净值 {acct.get('nav')}")
            if n:
                parts.append(f"{st.ID} {acct.get('last_date')}")
        nb = update_benchmarks(market, min(st.START for st in STRATEGIES))
        write_if_changed(STATE / "benchmarks.json", BENCHMARKS)
        write_if_changed(STATE / "strategies.json", [st.ID for st in STRATEGIES])
        log(f"benchmarks: 新增 {nb} 行")
        if args.git:
            git_push(", ".join(parts) or "benchmarks")
        status["ok"] = True
    except Exception as exc:
        status["error"] = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    status["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (CACHE / "last_run.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
