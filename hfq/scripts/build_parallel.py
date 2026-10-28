# -*- coding: utf-8 -*-
r"""并行调度 build_parquet.py：把交易日切成分组，多进程同时转换。

为什么需要它
------------
单日转换约 10 分钟（解压 ~48 GB CSV + 解析 + 写 Parquet），175 天串行要
28 小时。机器有 24 核、31 GB 内存，而每天写盘只有 4.6 GB、读盘 5 GB
（约 8 MB/s），远没打满 D: 那块 SATA 盘，瓶颈在 CPU —— 所以并发是纯赚。

安全性
------
* 每个进程只处理**互不相交**的交易日分组，分片目录天然不冲突；
* 唯一共享状态是 manifest，由 build_parquet.merge_manifest 用短临界区
  重读+合并+原子替换保护；
* 每组用独立槽位锁 ``.build-<k>.lock``，每轮开始前清理上一轮残留。

用法
----
    python hfq/scripts/build_parallel.py --workers 4
    python hfq/scripts/build_parallel.py --workers 4 --root D:\data-parquet \\
        --temp C:\Users\david\dev\finance\hfq\cache\_build --poll 120
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

from app.paths import archive_dir, parquet_default  # noqa: E402

BUILDER = os.path.join(HERE, "build_parquet.py")


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def commit_gb() -> tuple[float, float]:
    """(已提交GB, 提交上限GB)。

    这台机器物理内存 32 GB + 页面文件 32 GB，提交上限只有 ~63 GB；一旦被
    打满，Windows 会先杀掉桌面进程再整机卡死（2026-10-28 就这么挂过一次）。
    所以调度器必须自己盯着。
    """
    st = _MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(st)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    total = st.ullTotalPageFile / 1024 ** 3
    used = (st.ullTotalPageFile - st.ullAvailPageFile) / 1024 ** 3
    return used, total


def list_archives() -> list[str]:
    d = archive_dir()
    if not os.path.isdir(d):
        return []
    return sorted(fn[:-3] for fn in os.listdir(d)
                  if fn.endswith(".7z") and fn[:-3].isdigit())


def read_manifest(root: str) -> dict | None:
    p = os.path.join(root, "_meta", "manifest.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def clean_locks(root: str, slots: int) -> None:
    meta = os.path.join(root, "_meta")
    if not os.path.isdir(meta):
        return
    names = [".manifest.lock", ".build.lock"] + [f".build-{k}.lock" for k in range(slots)]
    for n in names:
        p = os.path.join(meta, n)
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"[sup] 清理残留锁 {n}", flush=True)
            except OSError:
                pass


def tail(path: str, n: int = 1) -> str:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 8192))
            raw = fh.read().decode("utf-8", "replace")
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        return " | ".join(lines[-n:])[-160:]
    except OSError:
        return ""


def run_pass(root: str, temp: str, dates: list[str], workers: int, pass_no: int,
             logdir: str, poll: int, max_commit: float = 45.0) -> list[str]:
    """跑一轮；返回本轮结束仍未进 manifest 的交易日。"""
    n = min(workers, len(dates))
    groups = [dates[i::n] for i in range(n)]
    procs = []
    logs = {}
    for k, g in enumerate(groups):
        if not g:
            continue
        logp = os.path.join(logdir, f"pass{pass_no}-w{k}.log")
        logs[k] = logp
        fh = open(logp, "w", encoding="utf-8", errors="replace")
        cmd = [sys.executable, BUILDER, "--root", root, "--temp", temp,
               "--slots", str(workers), "--dates", *g]
        print(f"[sup] 启动 worker {k}: {len(g)} 天 {g[0]}..{g[-1]} -> {logp}", flush=True)
        procs.append((k, g, subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT), fh))

    t0 = time.time()
    total = len(dates)
    reported: set[int] = set()
    while True:
        alive = [p for _k, _g, p, _fh in procs if p.poll() is None]
        m = read_manifest(root) or {"dates": {}}
        done = sum(1 for d in dates if d in m["dates"])
        elapsed = time.time() - t0
        eta = ""
        if done:
            per = elapsed / done
            eta = f" 预计剩余 {(total - done) * per / 3600:5.1f} 小时"
        used, limit = commit_gb()
        print(f"[sup] 轮 {pass_no}: {done}/{total} 天  {done / total * 100:5.1f}%  "
              f"用时 {elapsed / 3600:4.2f}h{eta}  活跃 {len(alive)}  "
              f"提交 {used:.1f}/{limit:.1f} GB", flush=True)
        if used > max_commit:
            for _k, _g, p, _fh in procs:
                if p.poll() is None:
                    p.terminate()
            raise SystemExit(
                f"提交内存 {used:.1f} GB 超过阈值 {max_commit:.0f} GB，已终止全部 worker"
                f"（这台机器提交上限只有 {limit:.0f} GB，打满会整机卡死）")
        for k, g, p, _fh in procs:
            if p.poll() is not None and k not in reported and k in logs:
                reported.add(k)
                print(f"[sup]   w{k} 已退出 rc={p.returncode}  末行: {tail(logs[k])}",
                      flush=True)
        if not alive:
            break
        time.sleep(poll)

    for k, g, p, fh in procs:
        fh.close()
        if p.returncode not in (0, None):
            print(f"[sup] worker {k} 非零退出 rc={p.returncode}，日志 {logs.get(k)}",
                  flush=True)

    m = read_manifest(root) or {"dates": {}}
    return [d for d in dates if d not in m["dates"]]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="并行跑 7z -> Parquet 转换")
    ap.add_argument("--root", default=parquet_default())
    ap.add_argument("--temp", default=os.path.join(HFQ, "cache", "_build"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--passes", type=int, default=6)
    ap.add_argument("--poll", type=int, default=120)
    ap.add_argument("--logdir", default=os.path.join(HFQ, "cache", "build-logs"))
    ap.add_argument("--dates", nargs="*", default=None, help="只转这些日（调试用）")
    ap.add_argument("--max-commit", type=float, default=45.0,
                    help="提交内存超过该值(GB)就终止全部 worker（本机上限 ~63 GB）")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    temp = os.path.abspath(args.temp)
    os.makedirs(temp, exist_ok=True)
    os.makedirs(args.logdir, exist_ok=True)
    os.makedirs(os.path.join(root, "_meta"), exist_ok=True)

    all_dates = list_archives()
    if not all_dates:
        raise SystemExit(f"未找到归档: {archive_dir()}")
    scope = args.dates or all_dates
    print(f"[sup] 归档 {len(all_dates)} 个 ({all_dates[0]}..{all_dates[-1]})，"
          f"本次范围 {len(scope)} 个", flush=True)
    print(f"[sup] 输出 {root}  临时 {temp}  并发 {args.workers}", flush=True)

    # 第一轮前先把 universe 建好：并行 worker 只读 universe，不写它
    if read_manifest(root) is None:
        print("[sup] 首次构建：先扫描全部归档生成 universe（不可并行，约 10 分钟）",
              flush=True)
        cmd = [sys.executable, BUILDER, "--root", root, "--temp", temp,
               "--universe-only"]
        rc = subprocess.call(cmd)
        if rc != 0:
            raise SystemExit(f"universe 构建失败 rc={rc}")
    clean_locks(root, args.workers)

    remaining = list(scope)
    for pass_no in range(1, args.passes + 1):
        m = read_manifest(root)
        if m is None:
            raise SystemExit("manifest 缺失，universe 构建可能失败")
        remaining = [d for d in scope if d not in m["dates"]]
        if not remaining:
            print(f"[sup] 全部完成：{len(m['dates'])} 个交易日", flush=True)
            break
        print(f"\n[sup] ===== 第 {pass_no} 轮，剩余 {len(remaining)} 天 "
              f"({os.path.basename(root)}) =====", flush=True)
        clean_locks(root, args.workers)
        before = len(m["dates"])
        remaining = run_pass(root, temp, remaining, args.workers, pass_no,
                             args.logdir, args.poll, args.max_commit)
        after = len(read_manifest(root)["dates"])
        if after == before:
            print("[sup] 本轮没有任何进展，停止（检查日志）", flush=True)
            break
        print(f"[sup] 第 {pass_no} 轮结束：+{after - before} 天，"
              f"剩余 {len(remaining)}", flush=True)

    m = read_manifest(root) or {"dates": {}}
    print(f"\n[sup] 数据集 {root}: {len(m['dates'])}/{len(scope)} 个交易日", flush=True)
    if remaining:
        print(f"[sup] 未完成 {len(remaining)} 个: {remaining[:10]}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
