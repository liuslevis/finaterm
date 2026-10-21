r"""批量转换看护器：逐个交易日调用 build_parquet，失败自动重试。

为什么需要它：一次跑几十小时的单进程很容易因为外部原因（终端/会话被回收、
审批策略变化）静默中断，而 build_parquet 本身是可断点续跑的。这里把
「逐日调用 + 失败重试 + 时间戳日志」串起来，中断后重跑同一条命令即可接续。

用法：
    python hfq/scripts/convert_all.py --root D:\data-lv2 --temp hfq/cache/_build
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
PY = sys.executable
BUILDER = os.path.join(HERE, "build_parquet.py")
sys.path.insert(0, HFQ)
from app.paths import archive_dir  # noqa: E402

DATA_DIR = archive_dir()


def ts() -> str:
    return time.strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def all_dates() -> list[str]:
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(fn[:-3] for fn in os.listdir(DATA_DIR)
                  if fn.endswith(".7z") and fn[:-3].isdigit())


def done_dates(root: str) -> set[str]:
    m = os.path.join(root, "_meta", "manifest.json")
    if not os.path.exists(m):
        return set()
    try:
        with open(m, encoding="utf-8") as fh:
            return set(json.load(fh).get("dates") or {})
    except (OSError, ValueError):
        return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--temp", default=os.path.join(HFQ, "cache", "_build"))
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--newest-first", action="store_true", default=True)
    ap.add_argument("--max-days", type=int, default=0, help="本次最多处理几天（0=全部）")
    args = ap.parse_args()

    # 临时目录必须以工作区为基准解析成绝对路径：builder 子进程的 cwd 是 hfq/，
    # 相对路径会被二次拼接成 hfq/hfq/cache/_build。
    args.temp = os.path.abspath(args.temp)
    args.root = os.path.abspath(args.root)

    alld = all_dates()
    if not alld:
        raise SystemExit(f"未找到归档: {DATA_DIR}")
    order = sorted(alld, reverse=args.newest_first)
    log(f"归档 {len(alld)} 天；已完成 {len(done_dates(args.root))} 天")

    processed = 0
    while True:
        pending = [d for d in order if d not in done_dates(args.root)]
        if not pending:
            log("全部交易日已转换完成")
            break
        if args.max_days and processed >= args.max_days:
            log(f"达到 --max-days={args.max_days}，停止（待处理 {len(pending)} 天）")
            break
        day = pending[0]
        log(f"开始 {day}（剩余 {len(pending)} 天）")
        t0 = time.perf_counter()
        ok = False
        for attempt in range(1, args.retries + 1):
            cmd = [PY, BUILDER, "--root", args.root, "--temp", args.temp,
                   "--reuse-temp", "--dates", day]
            rc = subprocess.call(cmd, cwd=HFQ)
            if rc == 0 and day in done_dates(args.root):
                ok = True
                break
            log(f"!! {day} 第 {attempt} 次失败 (exit={rc})，"
                f"{'重试' if attempt < args.retries else '跳过'}")
            time.sleep(5)
        if not ok:
            log(f"!! {day} 多次失败，放弃该日，继续下一天")
            # 落到列表末尾，避免死循环卡在同一天
            order.remove(day)
            order.append(day)
            processed += 1
            continue
        processed += 1
        log(f"完成 {day}  用时 {(time.perf_counter()-t0)/60:.1f} 分钟  "
            f"总进度 {len(done_dates(args.root))}/{len(all_dates())}")

    d = done_dates(args.root)
    log(f"结束：{len(d)}/{len(all_dates())} 天已转换")
    return 0 if len(d) == len(all_dates()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
