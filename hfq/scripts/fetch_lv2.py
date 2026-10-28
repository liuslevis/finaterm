# -*- coding: utf-8 -*-
r"""从 NAS 拉取 Level-2 日档（7z）到本地归档目录。

背景
----
远端 NAS（Synology）的 SSH 只开了 exec 通道，**没有** sftp 子系统，所以
``scp`` / ``sftp`` / ``rsync`` 都用不了（``subsystem request failed on channel 0``）。
唯一可行的通道是 ``ssh <host> cat <file>`` 的裸流：远端 ``cat`` 输出直接落到
本地临时文件的句柄上，全程不经过文本解码，不会损坏二进制。

为保证中断后不重复传输，每个文件先写 ``.tmp-<date>.7z``，校验大小一致后再
``os.replace`` 成正名；本地已存在且大小一致的文件直接跳过（幂等）。

用法
----
    python hfq/scripts/fetch_lv2.py                  # 增量拉全部缺失
    python hfq/scripts/fetch_lv2.py --dry-run        # 只列出要拉什么
    python hfq/scripts/fetch_lv2.py --months 202601,202602
    python hfq/scripts/fetch_lv2.py --workers 3      # 默认 3 条并发流

远端中文路径
------------
真实路径含中文（``.../Documents/量化/data-lv2``），跨平台传参容易踩编码坑。
脚本默认走 NAS 上预先建好的 ASCII 软链：

    ln -sfn "$(ls -d /volume1/homes/david/Documents/*/data-lv2)" \\
            /volume1/homes/david/lv2data

``--remote`` 可覆盖。
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HOST = "192.168.31.158"
PORT = 7891
REMOTE = "/volume1/homes/david/lv2data"
DEST = r"D:\data-lv2"

SSH_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=4",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "Compression=no",
    "-o", "LogLevel=ERROR",
]


def ssh_base(host: str, port: int) -> list[str]:
    return ["ssh", "-p", str(port), *SSH_OPTS, host]


def remote_list(host: str, port: int, remote: str) -> list[tuple[str, int, str]]:
    """返回 [(date, size, remote_path)]，按 date 升序。"""
    # -L：远端默认目录是个软链（ASCII 路径 -> 中文真实路径），
    # 不加 -L 时 find 只看到软链本身，会返回 0 条结果。
    cmd = f"find -L {shlex.quote(remote)} -mindepth 1 -maxdepth 2 -name '*.7z' -printf '%f\\t%s\\t%p\\n'"
    out = subprocess.run(
        [*ssh_base(host, port), cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        raise SystemExit(f"[fetch] 远端列目录失败 ({out.returncode}): {out.stderr.strip()}")
    rows: list[tuple[str, int, str]] = []
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        name, size, path = parts
        if not name.endswith(".7z"):
            continue
        date = name[:-3]
        if not date.isdigit():
            continue
        rows.append((date, int(size), path))
    rows.sort()
    # 远端偶有同一交易日同时落在相邻两个月目录里（换月边界重复上传），
    # 按 date 去重，保留先出现的那一份并提示。
    dedup: list[tuple[str, int, str]] = []
    seen: dict[str, str] = {}
    for date, size, path in rows:
        if date in seen:
            print(f"[fetch] 警告：{date} 远端重复 {seen[date]} / {path}，取前者", flush=True)
            continue
        seen[date] = path
        dedup.append((date, size, path))
    return dedup


def local_size(dest: str, date: str) -> int:
    p = os.path.join(dest, f"{date}.7z")
    try:
        return os.path.getsize(p)
    except OSError:
        return -1


def fetch_one(host: str, port: int, remote_path: str, dest: str, date: str,
              size: int, attempt_log: list[str]) -> tuple[str, int, float, str]:
    """拉单个文件；返回 (date, bytes, 秒, 状态)。"""
    final = os.path.join(dest, f"{date}.7z")
    tmp = os.path.join(dest, f".tmp-{date}.7z")
    base = [*ssh_base(host, port), f"cat {shlex.quote(remote_path)}"]

    last_err = ""
    for attempt in range(1, 4):
        t0 = time.time()
        # ssh 偶尔会在传输中挂死（实测有一次卡在 0 字节不动），必须自己掐表：
        # 按 8 MB/s 的下限速度给足余量，超时即杀掉重来。
        timeout = 600 + size / (8 * 1024 * 1024)
        try:
            with open(tmp, "wb") as fh:
                proc = subprocess.run(base, stdout=fh, stderr=subprocess.PIPE,
                                      timeout=timeout)
        except subprocess.TimeoutExpired:
            last_err = f"try{attempt}: 超时 {timeout:.0f}s"
            attempt_log.append(f"{date} {last_err}")
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            continue
        except OSError as e:  # noqa: BLE001
            last_err = f"本地写入失败: {e}"
            continue
        got = os.path.getsize(tmp) if os.path.exists(tmp) else -1
        dt = time.time() - t0
        if proc.returncode == 0 and got == size:
            os.replace(tmp, final)
            return date, got, dt, "ok"
        last_err = (f"try{attempt}: rc={proc.returncode} size={got}/{size} "
                    f"{proc.stderr.decode('utf-8', 'replace').strip()[:200]}")
        attempt_log.append(f"{date} {last_err}")
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        time.sleep(2 * attempt)

    return date, 0, 0.0, f"FAIL {last_err}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="从 NAS 增量拉取 LV2 7z 日档")
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--remote", default=REMOTE)
    ap.add_argument("--dest", default=DEST)
    ap.add_argument("--workers", type=int, default=3, help="并发 ssh 流数（1GbE 上 2~3 足够）")
    ap.add_argument("--months", default="", help="只拉这些月，逗号分隔，如 202601,202602")
    ap.add_argument("--limit", type=int, default=0, help="最多拉几个（调试用）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    dest = os.path.abspath(args.dest)
    os.makedirs(dest, exist_ok=True)

    months = {m.strip() for m in args.months.split(",") if m.strip()}

    print(f"[fetch] 读取远端清单 {args.host}:{args.port} {args.remote} ...", flush=True)
    rows = remote_list(args.host, args.port, args.remote)
    print(f"[fetch] 远端 {len(rows)} 个日档", flush=True)

    todo: list[tuple[str, int, str]] = []
    already = 0
    mismatch = 0
    for date, size, path in rows:
        if months and date[:6] not in months:
            continue
        have = local_size(dest, date)
        if have == size:
            already += 1
            continue
        if have >= 0:
            mismatch += 1
            print(f"[fetch] 大小不一致，重拉 {date}: 本地 {have} vs 远端 {size}", flush=True)
        todo.append((date, size, path))

    if args.limit:
        todo = todo[: args.limit]

    total = sum(t[1] for t in todo)
    print(f"[fetch] 目标目录 {dest}", flush=True)
    print(f"[fetch] 已完整 {already} 个 / 大小不符 {mismatch} 个 / 待拉 {len(todo)} 个 "
          f"({total / 1024 ** 3:.1f} GB)", flush=True)
    if args.dry_run:
        for date, size, _ in todo:
            print(f"  {date}  {size / 1024 ** 3:6.2f} GB")
        return 0
    if not todo:
        print("[fetch] 无需下载", flush=True)
        return 0

    # 清理上次中断留下的临时文件
    for fn in os.listdir(dest):
        if fn.startswith(".tmp-") and fn.endswith(".7z"):
            try:
                os.remove(os.path.join(dest, fn))
                print(f"[fetch] 清理残留 {fn}", flush=True)
            except OSError:
                pass

    t0 = time.time()
    done_bytes = 0
    ok = 0
    fails: list[str] = []
    attempt_log: list[str] = []
    n = len(todo)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {
            ex.submit(fetch_one, args.host, args.port, path, dest, date, size, attempt_log): (date, size)
            for date, size, path in todo
        }
        for fut in as_completed(futs):
            date, size = futs[fut]
            try:
                d, got, dt, status = fut.result()
            except Exception as e:  # noqa: BLE001
                fails.append(f"{date}: {e}")
                print(f"[fetch] {date} 异常 {e}", flush=True)
                continue
            elapsed = time.time() - t0
            if status == "ok":
                ok += 1
                done_bytes += got
                rate = got / 1024 ** 2 / max(dt, 1e-6)
                print(f"[fetch] {ok}/{n} {d} {got / 1024 ** 3:5.2f} GB {dt:5.1f}s "
                      f"{rate:6.1f} MB/s | 累计 {done_bytes / 1024 ** 3:6.1f} GB "
                      f"均速 {(done_bytes / 1024 ** 2) / max(elapsed, 1e-6):6.1f} MB/s",
                      flush=True)
            else:
                fails.append(f"{date}: {status}")
                print(f"[fetch] {date} 失败: {status}", flush=True)

            if (ok + len(fails)) % 10 == 0:
                left = total - done_bytes
                eta = left / max(done_bytes / max(elapsed, 1e-6), 1e-6)
                print(f"[fetch] ---- 剩余 {left / 1024 ** 3:6.1f} GB 预计 {eta / 60:5.1f} 分钟 ----",
                      flush=True)

    elapsed = time.time() - t0
    print(f"[fetch] 完成 {ok}/{n} 个，{done_bytes / 1024 ** 3:.1f} GB，"
          f"耗时 {elapsed / 60:.1f} 分钟，均速 {(done_bytes / 1024 ** 2) / max(elapsed, 1e-6):.1f} MB/s",
          flush=True)
    if fails:
        print(f"[fetch] 失败 {len(fails)} 个:", flush=True)
        for f in fails:
            print(f"  {f}", flush=True)
        return 1

    # 完整性复核：本地应有的文件是否都在、大小是否与远端一致
    bad = [(d, s) for d, s, _ in todo if local_size(dest, d) != s]
    if bad:
        print(f"[fetch] 复核不通过 {len(bad)} 个", flush=True)
        return 1
    print("[fetch] 复核通过（大小全部一致）", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
