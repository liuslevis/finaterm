"""Simple decision trees for QQQ quarterly DCA factors.

Train: id 1-20. Test: id 21-27.
Binary target: label > 0 (up vs down). Regression target: label (%).
"""

from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor, export_text

CSV = Path(__file__).with_name("qqq_dca_train.csv")
FEATURES = ["factor1", "factor2", "factor3", "factor4", "factor5", "factor6", "factor7"]


def load_split():
    df = pd.read_csv(CSV)
    # factor6 is blank until the quarter's 10-Q/10-K is out (2026Q3).
    df = df.dropna(subset=FEATURES)
    train = df[df["id"].between(1, 20)].copy()
    test = df[df["id"].between(21, 27)].copy()
    X_train, X_test = train[FEATURES], test[FEATURES]
    y_reg_train, y_reg_test = train["label"], test["label"]
    y_cls_train = (train["label"] > 0).astype(int)
    y_cls_test = (test["label"] > 0).astype(int)
    return train, test, X_train, X_test, y_cls_train, y_cls_test, y_reg_train, y_reg_test


def main():
    (
        train,
        test,
        X_train,
        X_test,
        y_cls_train,
        y_cls_test,
        y_reg_train,
        y_reg_test,
    ) = load_split()

    print(f"train n={len(train)}  test n={len(test)}")
    print(f"train up/down: {int(y_cls_train.sum())}/{int((1 - y_cls_train).sum())}")
    print(f"test  up/down: {int(y_cls_test.sum())}/{int((1 - y_cls_test).sum())}")

    # Keep trees shallow: n=20, 7 features.
    clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=2, random_state=0)
    clf.fit(X_train, y_cls_train)
    cls_pred = clf.predict(X_test)
    cls_prob = clf.predict_proba(X_test)[:, 1]

    print("\n===== BINARY CLASSIFICATION (label > 0) =====")
    print(export_text(clf, feature_names=FEATURES))
    print("feature importances:", dict(zip(FEATURES, clf.feature_importances_.round(3))))
    print("accuracy:", round(accuracy_score(y_cls_test, cls_pred), 3))
    print("confusion [[tn, fp], [fn, tp]]:\n", confusion_matrix(y_cls_test, cls_pred))
    print(classification_report(y_cls_test, cls_pred, target_names=["down", "up"], zero_division=0))

    print("id  quarter  actual%  actual_cls  pred_cls  P(up)")
    for row, y, p, pr in zip(test.itertuples(index=False), y_cls_test, cls_pred, cls_prob):
        print(
            f"{row.id:2d}  {row.year}Q{row.quarter}   {row.label:7.2f}     {y}         {p}      {pr:.2f}"
        )

    reg = DecisionTreeRegressor(max_depth=3, min_samples_leaf=2, random_state=0)
    reg.fit(X_train, y_reg_train)
    reg_pred = reg.predict(X_test)

    print("\n===== REGRESSION (label %) =====")
    print(export_text(reg, feature_names=FEATURES))
    print("feature importances:", dict(zip(FEATURES, reg.feature_importances_.round(3))))
    mae = mean_absolute_error(y_reg_test, reg_pred)
    rmse = mean_squared_error(y_reg_test, reg_pred) ** 0.5
    r2 = r2_score(y_reg_test, reg_pred)
    print(f"MAE={mae:.2f}  RMSE={rmse:.2f}  R2={r2:.3f}")
    print("sign accuracy (sign(pred)==sign(actual), 0 treated as down):",
          round(((reg_pred > 0) == (y_reg_test > 0)).mean(), 3))

    print("id  quarter  actual%   pred%   error")
    for row, p in zip(test.itertuples(index=False), reg_pred):
        print(f"{row.id:2d}  {row.year}Q{row.quarter}   {row.label:7.2f}  {p:7.2f}  {p - row.label:7.2f}")


if __name__ == "__main__":
    main()
