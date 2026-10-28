r"""7z 归档内部路径解析：兼容「嵌套」与「平铺」两种布局。

历史归档（2026-06-30 起）是嵌套的::

    20260921/000001.SZ/行情.csv

2026-01 ~ 2026-06 重新导出的归档是平铺的，少一层日期目录::

    000001.SZ/行情.csv

两者数据行完全一致。所有「从成员名里取股票代码」的地方都必须走
:func:`code_of`：按 ``parts[1]`` 硬取在平铺归档上会**静默**得到 0 只标的
（不报错，只是没有数据），这是最难发现的一类数据丢失。
"""

from __future__ import annotations

import os
import shutil
import subprocess

SUFFIXES = (".SZ", ".SH", ".BJ")
L2_FILES = ("行情.csv", "逐笔委托.csv", "逐笔成交.csv")

# 7-Zip 命令行。为什么不用 py7zr 解压：
#  * py7zr 1.1.3 对这些 3 万成员的单块归档做 extractall 会把解压结果整体
#    堆在内存里（实测虚拟内存冲到 110+ GB，把整机打到提交上限、桌面进程
#    崩掉重启）；
#  * 定向抽取也会偶发 ``Bad7zFile: Specified path is bad``（换个目标目录就复现），
#    因为它的路径校验在 Windows 上对 realpath 与父目录前缀的比对并不稳。
# 7z 命令行流式写盘、内存有界，解 45 GB 提交内存只涨几百 MB。
SEVEN_ZIP_CANDIDATES = [
    os.environ.get("HFQ_7Z", ""),
    r"C:\ProgramData\chocolatey\tools\7z.exe",
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe",
]


def seven_zip() -> str | None:
    """7z 可执行文件路径；找不到返回 None（调用方可回退 py7zr）。"""
    for c in SEVEN_ZIP_CANDIDATES:
        if c and os.path.exists(c):
            return c
    for name in ("7z", "7za", "7zr"):
        p = shutil.which(name)
        if p:
            return p
    return None


def extract(archive: str, dest: str, members: list[str] | None = None,
            timeout: float | None = 3600) -> None:
    """用 7z 命令行解压到 ``dest``。

    ``members`` 为成员名或通配模式（如 ``*000001.SZ*``）；None 表示全量。
    """
    exe = seven_zip()
    if exe is None:
        raise RuntimeError("未找到 7z 命令行，无法解压（HFQ_7Z 可指定路径）")
    os.makedirs(dest, exist_ok=True)
    cmd = [exe, "x", "-y", f"-o{dest}", archive, "-bso0", "-bsp0"]
    if members:
        cmd.extend(members)
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if proc.returncode not in (0, 1):  # 1 = 有警告但已解压
        tail = (proc.stdout or b"").decode("utf-8", "replace")[-300:] or \
               (proc.stderr or b"").decode("utf-8", "replace")[-300:]
        raise RuntimeError(f"7z rc={proc.returncode} {archive}: {tail.strip()}")


def _parts(member: str) -> list[str]:
    return [p for p in member.replace("\\", "/").split("/") if p]


def _looks_like_code(s: str) -> bool:
    return len(s) == 9 and s[6:] in SUFFIXES and s[:6].isdigit()


def code_of(member: str) -> str | None:
    """从归档成员名取出股票代码；取不到返回 ``None``。

    兼容 ``<date>/<code>/<file>`` 与 ``<code>/<file>`` 两种布局，也兼容
    py7zr 列出的目录条目（``<date>/<code>``）。
    """
    for p in _parts(member):
        if _looks_like_code(p):
            return p
    return None


def extract_root(member: str, stage_root: str) -> str:
    """成员被解压到 ``stage_root`` 之后，代码目录所在的父目录。

    嵌套布局是 ``stage_root/<date>``，平铺布局是 ``stage_root`` 本身。
    """
    parts = _parts(member)
    codes = [i for i, p in enumerate(parts) if _looks_like_code(p)]
    if not codes:
        return stage_root
    return os.path.join(stage_root, *parts[: codes[0]])


def find_stock_dir(stage_root: str, code: str) -> str | None:
    """解压完成后，在 ``stage_root`` 下定位某代码的 CSV 目录。

    不假定层级：只要目录名等于 ``code`` 且里面有三个 L2 CSV 之一即可。
    """
    for dirpath, _dirnames, filenames in os.walk(stage_root):
        if os.path.basename(dirpath) != code:
            continue
        if any(n in filenames for n in L2_FILES):
            return dirpath
    return None


__all__ = ["SUFFIXES", "L2_FILES", "code_of", "extract_root", "find_stock_dir",
           "seven_zip", "extract"]
