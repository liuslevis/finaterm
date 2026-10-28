# -*- coding: utf-8 -*-
r"""批量跑 ambush 的逐日信号生成（strategy.py），为回测准备 panel。

每个交易日一次 ``strategy.py --date <d>``，输出
``data/ambush_{kline_pool,limit_hits,results,candidates,evaluation}_<d>.csv``。
已存在 ``ambush_results_<d>.csv`` 的日期默认跳过（幂等，断点续跑）。

用法
----
    python predictor/ambush/run_history.py                 # 补齐所有缺失日期
    python predictor/ambush/run_history.py --from 20260105 --to 20260630
    python predictor/ambush/run_history.py --force --dates 20260105 20260106

跑完再用 optimize_score.py 在完整 panel 上做训练/测试与净值回测：
    python predictor/ambush/optimize_score.py --train-from 20260105 \
        --train-through 20260630 --test-through 20260921 --evaluate-validation
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import strategy as st  # noqa: E402


def archive_dates() -> list[str]:
    return sorted(p.stem for p in st.DATA_DIR.glob("*.7z") if p.stem.isdigit())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="date_from", default=None)
    ap.add_argument("--to", dest="date_to", default=None)
    ap.add_argument("--dates", nargs="*", default=None)
    ap.add_argument("--force", action="store_true", help="已有结果也重跑")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--logdir", default=os.path.join(st.HFQ_DIR, "cache", "ambush", "logs"))
    ap.add_argument("--allow-kline-fetch", action="store_true",
                    help="允许联网补 K 线（默认离线：只用缓存，缺的跳过）")
    args = ap.parse_args(argv)

    os.makedirs(args.logdir, exist_ok=True)
    dates = args.dates or archive_dates()
    if args.date_from:
        dates = [d for d in dates if d >= args.date_from]
    if args.date_to:
        dates = [d for d in dates if d <= args.date_to]

    todo = []
    for d in dates:
        if args.force or not (st.OUTPUT_DIR / f"ambush_results_{d}.csv").exists():
            todo.append(d)
    print(f"归档 {len(dates)} 天，待跑 {len(todo)} 天", flush=True)
    if not todo:
        return 0

    t0 = time.time()
    ok = fail = 0
    failed: list[tuple[str, str]] = []
    for i, d in enumerate(todo, 1):
        logp = os.path.join(args.logdir, f"strategy-{d}.log")
        t = time.time()
        try:
            cmd = [sys.executable, "-u", "strategy.py", "--date", d]
            if not args.allow_kline_fetch:
                cmd.append("--offline-klines")
            with open(logp, "w", encoding="utf-8", errors="replace") as fh:
                proc = subprocess.run(
                    cmd,
                    cwd=HERE, stdout=fh, stderr=subprocess.STDOUT,
                    timeout=args.timeout,
                )
        except subprocess.TimeoutExpired:
            fail += 1
            failed.append((d, f"超时 {args.timeout}s"))
            print(f"[{i}/{len(todo)}] {d} 超时", flush=True)
            continue
        dt = time.time() - t
        if proc.returncode == 0:
            ok += 1
            print(f"[{i}/{len(todo)}] {d} ok {dt:5.0f}s  "
                  f"累计 {(time.time()-t0)/60:5.1f} 分钟", flush=True)
        else:
            fail += 1
            tail = ""
            try:
                with open(logp, encoding="utf-8", errors="replace") as fh:
                    lines = [ln.strip() for ln in fh if ln.strip()]
                tail = " | ".join(lines[-2:])[-200:]
            except OSError:
                pass
            failed.append((d, tail))
            print(f"[{i}/{len(todo)}] {d} FAIL rc={proc.returncode}  {tail}", flush=True)

    print(f"\n完成 {ok}，失败 {fail}，耗时 {(time.time()-t0)/60:.1f} 分钟", flush=True)
    for d, why in failed:
        print(f"  {d}: {why}", flush=True)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
