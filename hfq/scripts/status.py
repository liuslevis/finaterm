"""转换进度速查：`python hfq/scripts/status.py`。"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
ROOT = os.environ.get("HFQ_MAIN_DS") or os.path.join(HFQ, "data-parquet")


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
    left = 59 - len(ds)
    last = max(ds, key=lambda k: d[k]["built_at"]) if ds else "-"
    lock = os.path.join(ROOT, "_meta", ".build.lock")
    print(f"{len(ds)}/59 天  剩余 {left} 天约 {med * left / 3600:.1f} h  "
          f"最近构建 {last}  锁={'有' if os.path.exists(lock) else '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
