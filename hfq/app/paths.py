r"""数据目录解析：Parquet 数据集与 7z 归档的位置。

两者可以分开存放，也可以放在同一块盘：

    归档    D:\data-lv2       874 GB（2026-01~09，175 个日档）
    Parquet D:\data-parquet   839 GB（175 天，11,191 只，44 分片）

2026-10-28 的布局调整：Parquet 从 C: 挪到 D:。扩到 175 天需要 839 GB，而
C: 只剩 ~450 GB，放不下；C: 留给转换的临时目录（每秒几百 MB 的写入，
NVMe 比机械盘快一个数量级）。

所有位置都支持环境变量覆盖，便于迁移或放到别的盘：

    归档：HFQ_ARCHIVE_DIR
       1. 环境变量
       2. <repo>/hfq/data-lv2
       3. D:\data-lv2

    Parquet：HFQ_PARQUET_DIR
       1. 环境变量
       2. D:\data-parquet
       3. <repo>/hfq/data-parquet
"""

from __future__ import annotations

import os

HFQ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARCHIVE_ENV = "HFQ_ARCHIVE_DIR"
PARQUET_ENV = "HFQ_PARQUET_DIR"

ARCHIVE_CANDIDATES: list[str] = [
    os.path.join(HFQ, "data-lv2"),
    r"D:\data-lv2",
]
PARQUET_CANDIDATES: list[str] = [
    r"D:\data-parquet",
    os.path.join(HFQ, "data-parquet"),
]


def _first_existing(env: str, candidates: list[str]) -> str:
    env_val = os.environ.get(env, "").strip()
    if env_val:
        return os.path.abspath(env_val)
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[-1]


def archive_dir() -> str:
    """7z 归档所在目录。"""
    return _first_existing(ARCHIVE_ENV, ARCHIVE_CANDIDATES)


def parquet_candidates() -> list[str]:
    """Parquet 数据集候选位置（按优先级；调用方逐个探测）。"""
    env_val = os.environ.get(PARQUET_ENV, "").strip()
    return ([os.path.abspath(env_val)] if env_val else []) + PARQUET_CANDIDATES


def parquet_default() -> str:
    return PARQUET_CANDIDATES[0]


__all__ = ["HFQ", "archive_dir", "parquet_candidates", "parquet_default",
           "ARCHIVE_CANDIDATES", "PARQUET_CANDIDATES", "ARCHIVE_ENV", "PARQUET_ENV"]
