"""Export the appendix sample list of ambush candidates and strategy hits."""

from __future__ import annotations

import argparse

import pandas as pd
from optimize_score import (
    DATA_DIR,
    EXTRA_FEATURE_SETS,
    EVALUATION_HORIZONS,
    apply_models,
    features_are_trainable,
    load_panel,
    rank_panel,
    split_datasets,
    train_direction_model,
    train_ridge_model,
)

SCORE_LABELS = {
    "lv2_score": "LV2",
    "lv2_score_pre_sol61": "PRE61",
    "lv2_score_v2_baseline": "V2",
    "lv2_score_v3": "V3",
    "lv2_score_v4": "V4",
    "lv2_score_v5": "V5",
    "lv2_score_v5_fixed": "V5F",
    "lv2_score_v6": "V6",
    "lv2_score_v6_fixed": "V6F",
    "lv2_score_v7": "V7",
    "lv2_score_v7_fixed": "V7F",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-from", default="20260601")
    parser.add_argument("--train-through", default="20260731")
    parser.add_argument("--test-through", default="20260831")
    parser.add_argument("--validation-through", default="20260930")
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print the appendix table as markdown rows for README.md",
    )
    return parser.parse_args()


def mark_top_half_hits(panel: pd.DataFrame) -> pd.DataFrame:
    marked = panel.copy()
    for score_column in SCORE_LABELS:
        flags = pd.Series(False, index=marked.index)
        if score_column not in marked:
            marked[f"hit_{score_column}"] = flags
            continue
        for _, group in marked.groupby("signal_date"):
            ranked = group.dropna(subset=[score_column])
            if ranked.empty:
                continue
            top_count = (len(ranked) + 1) // 2
            flags.loc[ranked.nlargest(top_count, score_column).index] = True
        marked[f"hit_{score_column}"] = flags
    marked["hit_strategies"] = [
        ";".join(
            label
            for score_column, label in SCORE_LABELS.items()
            if row[f"hit_{score_column}"]
        )
        for _, row in marked.iterrows()
    ]
    marked["hit_count"] = sum(
        marked[f"hit_{score_column}"].astype(int) for score_column in SCORE_LABELS
    )
    return marked


def format_pct(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:+.2f}%"


def main() -> None:
    args = parse_args()
    panel = load_panel(args.train_from, args.validation_through)
    eligible = rank_panel(panel[
        panel["launch_detected"].astype(bool)
        & panel["data_quality_valid"].astype(bool)
    ].copy())
    train, test, validation = split_datasets(
        eligible,
        args.train_from,
        args.train_through,
        args.test_through,
        args.validation_through,
    )
    model_v3 = train_direction_model(train)
    model_v4 = train_ridge_model(train)
    extra_models = {
        score_name: (
            train_ridge_model(train, features)
            if features_are_trainable(train, features)
            else None
        )
        for score_name, features in EXTRA_FEATURE_SETS.items()
    }
    scored = apply_models(eligible, model_v3, model_v4, extra_models)
    scored["dataset_split"] = "excluded"
    scored.loc[scored.index.isin(train.index), "dataset_split"] = "train"
    scored.loc[scored.index.isin(test.index), "dataset_split"] = "test"
    scored.loc[scored.index.isin(validation.index), "dataset_split"] = "validation"
    scored = mark_top_half_hits(scored)

    columns = [
        "signal_date",
        "code",
        "name",
        "dataset_split",
        "dormancy_score",
        "trigger_score",
        *[f"forward_{horizon}_pct" for horizon in EVALUATION_HORIZONS],
        "hit_count",
        "hit_strategies",
        *[f"hit_{score_column}" for score_column in SCORE_LABELS],
    ]
    appendix = scored[columns].sort_values(
        ["signal_date", "hit_count", "code"],
        ascending=[True, False, True],
    )
    output = (
        DATA_DIR
        / f"ambush_sample_appendix_{args.train_from}_{args.validation_through}.csv"
    )
    appendix.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"{len(appendix)} samples written to {output}")
    print(appendix.groupby("dataset_split")["code"].count().to_string())
    if not args.markdown:
        return
    print(
        "| 入选日期 | 代码 | 名称 | 数据集 | 3D | 1W | 3W | 命中数 | 命中策略 |"
    )
    print("|---|---|---|---|---:|---:|---:|---:|---|")
    for _, row in appendix.iterrows():
        code = str(row["code"]).zfill(6)
        print(
            f"| {row['signal_date']} | {code} | {row['name']} "
            f"| {row['dataset_split']} "
            f"| {format_pct(row['forward_3d_pct'])} "
            f"| {format_pct(row['forward_1w_pct'])} "
            f"| {format_pct(row['forward_3w_pct'])} "
            f"| {row['hit_count']} | {row['hit_strategies'] or '—'} |"
        )


if __name__ == "__main__":
    main()
