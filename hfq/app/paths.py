r"""数据目录解析：Parquet 数据集与 7z 归档的位置。

两者可以分开存放（本机就是 Parquet 在 C: 快盘、7z 归档在 D: 慢盘）。
所有位置都支持环境变量覆盖，便于迁移或放到别的盘：

    归档：HFQ_ARCHIVE_DIR
       1. 环境变量
       2. <repo>/hfq/data-lv2      （默认）
       3. D:\data-lv2              （归档挪到别的盘时）

    Parquet：HFQ_PARQUET_DIR
       1. 环境变量
       2. <repo>/hfq/data-parquet （默认）
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
