"""修改前快照：固化源码、数据清单与行为基线。

工作区已有大量未提交改动，因此快照不复用 git，而是自包含地记录：
  code/            将被修改的源码原样副本（含整个 app 包，可独立重跑基线）
  inventory.json   data-lv2 归档清单与体积
  behavior/        逐 (date, code) 的派生结果指纹与样本
  perf.json        基线耗时
  SHA256SUMS       全部快照文件的校验和

用法：python hfq/scripts/snapshot.py [--tag NAME]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
ROOT = os.path.dirname(HFQ)
sys.path.insert(0, HFQ)

# 参与快照的源码（将被修改 / 新建）
SNAPSHOT_SOURCES = [
    "app/__init__.py",
    "app/data.py",
    "server.py",
    "scripts/snapshot.py",
]

SNAP_ROOT = os.path.join(HFQ, "snapshot")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# 行为指纹
# --------------------------------------------------------------------------- #
def _digest(obj) -> str:
    return sha256_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                   default=float, separators=(",", ":")).encode())


def probe_behavior(date: str, code: str) -> dict:
    """跑一遍全部派生结构，记录指纹 + 可读样本。"""
    from app import data

    t0 = time.perf_counter()
    sd = data.get_stock(code, date)
    t_load = time.perf_counter() - t0

    ev = sd.events
    quotes = sd.quotes
    ladder = data.build_ladder(sd)
    books = data.all_books(sd)
    intr = data.intraday(sd)
    all_ev = data.filter_events(sd)
    summary = data.summarize(all_ev)
    first_order = sd.orders_summary[0]["order_id"] if sd.orders_summary else None
    track = data.track_order(sd, first_order) if first_order is not None else {}
    locate = data.locate_order(sd, first_order) if first_order is not None else {}
    book = data.order_book_at(sd, 100000000)
    orders = data.list_orders(sd, limit=50)

    # 事件流完整指纹（逐字段），确保任何解析差异都能被发现
    ev_fp = _digest([[e["aseq"], e["t"], e["type"], e["side"],
                      round(e["price"], 6), e["qty"], e["buy_id"], e["sell_id"],
                      e["order_id"], round(e["amount"], 6)] for e in ev])
    q_fp = _digest([[q["t"], round(q["last"], 6), q["cum_vol"], q["cum_amt"],
                     round(q["high"], 6), round(q["low"], 6), round(q["open"], 6),
                     round(q["prev_close"], 6),
                     [[round(p, 6), n] for p, n in q["asks"]],
                     [[round(p, 6), n] for p, n in q["bids"]]] for q in quotes])

    return {
        "date": date, "code": code,
        "counts": {"events": len(ev), "quotes": len(quotes),
                   "orders_summary": len(sd.orders_summary),
                   "ladder": len(ladder), "intraday_points": len(intr["points"])},
        "fingerprints": {"events": ev_fp, "quotes": q_fp,
                         "basic": _digest(sd.basic), "ladder": _digest(ladder),
                         "all_books": _digest(books), "intraday": _digest(intr),
                         "summary": _digest(summary), "track": _digest(track),
                         "locate": _digest(locate), "orderbook": _digest(book),
                         "orders_head": _digest(orders),
                         "events_head50": _digest(
                             [[e["seq"], e["t"], e["type"], e["side"],
                               round(e["price"], 6), e["qty"]] for e in ev[:50]]),
                         "events_tail50": _digest(
                             [[e["seq"], e["t"], e["type"], e["side"],
                               round(e["price"], 6), e["qty"]] for e in ev[-50:]])},
        "samples": {"basic": sd.basic,
                    "first_event": ev[0] if ev else None,
                    "last_event": ev[-1] if ev else None,
                    "first_quote": quotes[0] if quotes else None,
                    "summary": summary},
        "load_seconds": round(t_load, 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=time.strftime("baseline-%Y%m%d-%H%M%S"))
    ap.add_argument("--dates", nargs="*", default=None,
                    help="默认取 cache 下已有抽取的交易日")
    args = ap.parse_args()

    out = os.path.join(SNAP_ROOT, args.tag)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "code"), exist_ok=True)
    os.makedirs(os.path.join(out, "behavior"), exist_ok=True)

    print(f"快照 -> {out}")

    # 1) 源码副本
    copied = {}
    for rel in SNAPSHOT_SOURCES:
        src = os.path.join(HFQ, rel)
        if not os.path.exists(src):
            print(f"  skip (缺失) {rel}")
            continue
        dst = os.path.join(out, "code", rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied[rel] = {"sha256": sha256_file(src), "bytes": os.path.getsize(src)}
        print(f"  code  {rel}  {os.path.getsize(src):>8} B  {copied[rel]['sha256'][:16]}")

    # 2) 数据清单
    data_dir = os.path.join(HFQ, "data-lv2")
    inv_dates = []
    total = 0
    for fn in sorted(os.listdir(data_dir)):
        if not (fn.endswith(".7z") and fn[:-3].isdigit()):
            continue
        p = os.path.join(data_dir, fn)
        sz = os.path.getsize(p)
        total += sz
        inv_dates.append({"date": fn[:-3], "bytes": sz,
                          "mtime": int(os.path.getmtime(p))})
    inventory = {
        "data_dir": data_dir,
        "archive_count": len(inv_dates),
        "total_bytes": total,
        "dates": inv_dates,
        "cache_dir_bytes": sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, fs in os.walk(os.path.join(HFQ, "cache")) for f in fs),
        "cache_dates": sorted(d for d in os.listdir(os.path.join(HFQ, "cache"))
                              if d.isdigit()),
    }
    with open(os.path.join(out, "inventory.json"), "w", encoding="utf-8") as fh:
        json.dump(inventory, fh, indent=2, ensure_ascii=False)
    print(f"  inventory  {inventory['archive_count']} 个归档, "
          f"{total/1024**3:.2f} GB")

    # 3) 行为基线
    from app import data

    dates = args.dates or sorted(
        d for d in os.listdir(os.path.join(HFQ, "cache")) if d.isdigit())
    if not dates:
        print("  ! 无已抽取缓存，跳过行为基线")
        return

    probes = []
    for date in dates:
        ddir = os.path.join(HFQ, "cache", date)
        codes = sorted(
            c for c in os.listdir(ddir)
            if not c.startswith("_") and os.path.isdir(os.path.join(ddir, c)))
        for code in codes:
            try:
                r = probe_behavior(date, code)
            except Exception as e:  # noqa: BLE001
                r = {"date": date, "code": code, "error": f"{type(e).__name__}: {e}"}
            probes.append(r)
            fn = f"{date}__{code}.json".replace(".", "_")
            with open(os.path.join(out, "behavior", fn), "w", encoding="utf-8") as fh:
                json.dump(r, fh, indent=2, ensure_ascii=False, default=str)
            if "error" in r:
                print(f"  behavior {date}/{code}  ERROR {r['error']}")
            else:
                print(f"  behavior {date}/{code}  events={r['counts']['events']:>7} "
                      f"quotes={r['counts']['quotes']:>5}  {r['load_seconds']:.2f}s")

    perf = {"probes": [{"date": p["date"], "code": p["code"],
                        "load_seconds": p.get("load_seconds")} for p in probes],
            "note": "load_seconds 为 get_stock 单次耗时（基线含 7z 抽取+CSV 解析或二进制缓存）"}
    with open(os.path.join(out, "perf.json"), "w", encoding="utf-8") as fh:
        json.dump(perf, fh, indent=2, ensure_ascii=False)

    # 4) 校验和
    lines = []
    for dp, _, fs in os.walk(out):
        for f in sorted(fs):
            if f == "SHA256SUMS":
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, out).replace(os.sep, "/")
            lines.append(f"{sha256_file(p)}  {rel}")
    with open(os.path.join(out, "SHA256SUMS"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(lines)) + "\n")

    print(f"\n完成：{len(probes)} 个行为探针，"
          f"{len(lines)} 个快照文件 -> {out}")


if __name__ == "__main__":
    main()
