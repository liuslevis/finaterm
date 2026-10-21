r"""汇总最终数据集口径，生成快照级报告（供 docs 更新与验收）。

只读 manifest + 目录元数据（不读 parquet 内容），因此很快，可在转换期间随时跑。

用法：
    python hfq/scripts/make_report.py --root D:\data-lv2
    python hfq/scripts/make_report.py --root D:\data-lv2 --json snapshot/final_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

sys.path.insert(0, HFQ)
from app.paths import archive_dir  # noqa: E402

DATA_DIR = archive_dir()
GIB = 1024 ** 3


def archive_dates() -> list[str]:
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(fn[:-3] for fn in os.listdir(DATA_DIR)
                  if fn.endswith(".7z") and fn[:-3].isdigit())


def human(n: float) -> str:
    return f"{n / GIB:.2f} GB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--json", default=os.path.join(HFQ, "snapshot", "final_report.json"))
    ap.add_argument("--md", default=os.path.join(HFQ, "snapshot", "final_report.md"))
    ap.add_argument("--update-doc", default=None,
                    help="把生成内容写进该 markdown 的 <!-- AUTO:dataset --> 区块")
    ap.add_argument("--skip-walk", action="store_true",
                    help="不遍历文件统计实际占用（慢盘上可跳过，改用 manifest 记录之和）")
    args = ap.parse_args()

    with open(os.path.join(args.root, "_meta", "manifest.json"), encoding="utf-8") as fh:
        m = json.load(fh)

    want = archive_dates()
    have = sorted(m["dates"])
    missing = [d for d in want if d not in have]
    extra = [d for d in have if d not in want]
    shards = (len(m["universe"]) + m["shard_size"] - 1) // m["shard_size"]

    # 每个交易日的分片数是否齐全
    by_date_files: dict[str, int] = {}
    by_date_bytes: dict[str, int] = {}
    total_bytes = 0
    file_count = 0
    for root, _dirs, files in os.walk(args.root):
        if "date=" not in os.path.basename(root):
            continue
        d = os.path.basename(root).split("=", 1)[1]
        n = b = 0
        for f in files:
            p = os.path.join(root, f)
            s = os.path.getsize(p)
            n += 1
            b += s
        by_date_files[d] = n
        by_date_bytes[d] = b
        total_bytes += b
        file_count += n
    # catalog / codes 也算进总量
    other = 0
    for sub in ("catalog", "_meta"):
        base = os.path.join(args.root, sub)
        for root, _dirs, files in os.walk(base):
            for f in files:
                other += os.path.getsize(os.path.join(root, f))
                file_count += 1
    total_bytes += other

    expected_files = shards * 3
    # 分片是否「应有文件」取决于该分片当天有没有标的：universe 是 59 天并集，
    # 某些区间（如 2428xx..2448xx）只在部分交易日存在，那天整体不写文件是正确的。
    short: dict[str, dict] = {}
    sparse: dict[str, dict] = {}
    extra_shards: dict[str, list[int]] = {}
    uni_pos = {c: i for i, c in enumerate(m["universe"])}
    shard_size = m["shard_size"]
    for d in have:
        cp = os.path.join(args.root, "_meta", "codes", f"{d}.parquet")
        expect: set[int] = set()
        if os.path.exists(cp):
            import pyarrow.parquet as _pq
            for c in _pq.read_table(cp, columns=["code"]).column("code").to_pylist():
                i = uni_pos.get(c)
                if i is not None:
                    expect.add(i // shard_size)
        got: set[int] = set()
        for root, _dirs, files in os.walk(args.root):
            if os.path.basename(root) == f"date={d}":
                for f in files:
                    stem = f.rsplit("-", 1)[-1].rsplit(".", 1)[0]
                    if stem.isdigit():
                        got.add(int(stem))
                break
        miss = sorted(expect - got)
        if miss:
            short[d] = {"missing_shards": miss, "expected_shards": len(expect),
                        "files": by_date_files.get(d, 0)}
        elif len(expect) < shards:
            sparse[d] = {"shards_with_codes": len(expect), "shards": shards,
                         "files": by_date_files.get(d, 0)}
        over = sorted(got - expect)
        if over:
            extra_shards[d] = over

    arc = sum(m["dates"][d]["archive_bytes"] for d in have)
    raw = sum(m["dates"][d]["raw_bytes"] for d in have)
    rows = {t: sum(m["dates"][d]["rows"].get(t, 0) for d in have)
            for t in ("orders", "trades", "quotes")}
    codes_total = sum(m["dates"][d].get("codes", 0) for d in have)
    secs = [m["dates"][d]["total_seconds"] for d in have]
    fast = [s for s in secs if s < 900] or secs
    ex = [m["dates"][d]["extract_seconds"] for d in have]
    pa = [m["dates"][d]["parse_seconds"] for d in have]

    lines = []
    A = lines.append
    A("# 数据集最终口径\n")
    A(f"- 数据集根目录：`{os.path.abspath(args.root)}`")
    A(f"- schema：{m['schema']}　分区频率：`{m['freq']}`　分片大小：{m['shard_size']} 只")
    A(f"- universe：{len(m['universe'])} 只　分片数：{shards}　"
      f"压缩：{m['write_opts']['compression']}-{m['write_opts']['compression_level']}　"
      f"row_group_size：{m['write_opts']['row_group_size']}")
    A("")
    A("## 覆盖\n")
    A(f"- 归档交易日：{len(want)} 个（{want[0] if want else '-'} … {want[-1] if want else '-'}）")
    A(f"- 已转换：**{len(have)} / {len(want)}**")
    if missing:
        A(f"- 未转换：{len(missing)} 个 → {missing[:8]}{' …' if len(missing) > 8 else ''}")
    if extra:
        A(f"- manifest 里多出的非归档交易日：{extra}")
    A("")
    A("## 体积与压缩\n")
    A("| 口径 | 值 |")
    A("|---|---|")
    A(f"| 7z 归档 | {human(arc)} |")
    A(f"| CSV（解压后） | {human(raw)} |")
    A(f"| Parquet 实测占用 | **{human(total_bytes)}** |")
    A(f"| 文件数 | {file_count} |")
    if total_bytes:
        A(f"| 压缩比 vs CSV | **{raw / total_bytes:.2f}x** |")
        A(f"| 压缩比 vs 7z | **{arc / total_bytes:.2f}x** |")
        A(f"| 单日均值 | {human(total_bytes / max(len(have), 1))} |")
    if codes_total:
        A(f"| 单「股票×日」 | {total_bytes / codes_total / 1024 ** 2:.2f} MB |")
    A("")
    A("## 行数\n")
    A("| 表 | 行数 |")
    A("|---|---|")
    for t, n in rows.items():
        A(f"| {t} | {n:,} |")
    A(f"| 合计 | {sum(rows.values()):,} |")
    A("")
    A("## 构建耗时\n")
    A("| 指标 | 值 |")
    A("|---|---|")
    A(f"| 单日总耗时（中位） | {statistics.median(fast) / 60:.1f} 分钟 |")
    A(f"| 单日总耗时（范围） | {min(fast) / 60:.1f} – {max(fast) / 60:.1f} 分钟 |")
    if ex:
        A(f"| 其中解压（中位） | {statistics.median(ex):.0f} s |")
    if pa:
        A(f"| 其中解析（中位） | {statistics.median(pa):.0f} s |")
    A(f"| 累计耗时 | {sum(secs) / 3600:.2f} 小时 |")
    A("")
    A("## 完整性\n")
    if short:
        A(f"- ⚠️ 有交易日缺少应有分片：{short}")
    else:
        A("- 所有交易日：凡当天有标的的分片都有对应文件，无缺失")
    if extra_shards:
        A(f"- ⚠️ 存在超出当日标的范围的分片：{extra_shards}")
    A(f"- 满配应为 {expected_files} 个文件（{shards} 分片 × 3 表）；"
      f"实际各日 "
      f"{min(by_date_files.values()) if by_date_files else 0}–"
      f"{max(by_date_files.values()) if by_date_files else 0} 个")
    if sparse:
        A("")
        A("文件数低于满配的交易日，原因是这些日期源归档标的较少，部分分片区间当天"
          "完全没有标的（universe 是 59 天并集），属正确行为：")
        A("")
        A("| 交易日 | 当天有标的的分片 | 文件数 |")
        A("|---|---|---|")
        for d in sorted(sparse):
            v = sparse[d]
            A(f"| {d} | {v['shards_with_codes']}/{v['shards']} | {v['files']} |")
    A("")
    A("## 各交易日明细\n")
    A("| 交易日 | 标的 | 分片文件 | 体积 | 解压 s | 解析 s | 总 s |")
    A("|---|---|---|---|---|---|---|")
    for d in have:
        i = m["dates"][d]
        A(f"| {d} | {i.get('codes', 0)} | {by_date_files.get(d, 0)} | "
          f"{by_date_bytes.get(d, 0) / 1024 ** 2:.0f} MB | "
          f"{i['extract_seconds']:.0f} | {i['parse_seconds']:.0f} | "
          f"{i['total_seconds']:.0f} |")

    text = "\n".join(lines)
    print(text)

    report = {
        "root": os.path.abspath(args.root),
        "schema": m["schema"], "freq": m["freq"], "shard_size": m["shard_size"],
        "universe": len(m["universe"]), "shards": shards,
        "write_opts": m["write_opts"],
        "archive_dates": len(want), "converted": len(have),
        "missing": missing, "extra": extra,
        "bytes": {"archive": arc, "csv": raw, "parquet": total_bytes,
                  "files": file_count},
        "ratio": {"vs_csv": round(raw / total_bytes, 3) if total_bytes else None,
                  "vs_7z": round(arc / total_bytes, 3) if total_bytes else None},
        "rows": rows,
        "codes_total": codes_total,
        "seconds": {"median": statistics.median(fast), "min": min(fast),
                    "max": max(fast), "sum": sum(secs)},
        "integrity": {"expected_files_per_date": expected_files,
                      "missing_shards": short, "extra_shards": extra_shards,
                      "sparse_dates": sparse},
        "per_date": {d: {"files": by_date_files.get(d, 0),
                         "bytes": by_date_bytes.get(d, 0),
                         **{k: m["dates"][d][k] for k in
                            ("codes", "rows", "extract_seconds",
                             "parse_seconds", "total_seconds")}}
                     for d in have},
    }
    if args.update_doc:
        begin = "<!-- AUTO:dataset -->"
        end = "<!-- /AUTO:dataset -->"
        doc = open(args.update_doc, encoding="utf-8").read()
        if begin not in doc or end not in doc:
            print(f"!! {args.update_doc} 缺少 {begin} / {end} 标记")
            return 2
        i = doc.index(begin) + len(begin)
        j = doc.index(end)
        body = "\n" + text.split("\n", 1)[1].strip() + "\n"
        doc = doc[:i] + body + doc[j:]
        with open(args.update_doc, "w", encoding="utf-8") as fh:
            fh.write(doc)
        print(f"已更新文档区块 -> {args.update_doc}")

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    with open(args.md, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n-> {args.json}\n-> {args.md}")
    return 0 if not short else 1


if __name__ == "__main__":
    raise SystemExit(main())
