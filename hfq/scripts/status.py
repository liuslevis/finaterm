"""转换进度速查：`python hfq/scripts/status.py`。"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

from app.paths import archive_dir, parquet_default  # noqa: E402

ROOT = os.environ.get("HFQ_MAIN_DS") or parquet_default()


def _target_days() -> int:
    """目标交易日数 = 归档里日档的个数（此前硬编码 59，随数据集扩容已失真）。"""
    try:
        return sum(1 for fn in os.listdir(archive_dir())
                   if fn.endswith(".7z") and fn[:-3].isdigit())
    except OSError:
        return 0


def main() -> int:
    mpath = os.path.join(ROOT, "_meta", "manifest.json")
    if not os.path.exists(mpath):
        print(f"无 manifest: {mpath}")
        return 1
    with open(mpath, encoding="utf-8") as fh:
        m = json.load(fh)
    d = m["dates"]
    ds = sorted(d)
    fast = [d[k]["total_seconds"] for k in ds if d[k]["total_seconds"] < 900]
    med = sum(fast) / len(fast) if fast else 0
    target = _target_days() or len(ds)
    left = target - len(ds)
    last = max(ds, key=lambda k: d[k]["built_at"]) if ds else "-"
    lock = os.path.join(ROOT, "_meta", ".build.lock")
    print(f"{len(ds)}/{target} 天  剩余 {left} 天约 {med * max(left, 0) / 3600:.1f} h  "
          f"最近构建 {last}  锁={'有' if os.path.exists(lock) else '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
