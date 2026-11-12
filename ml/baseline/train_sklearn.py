import json
import re
import time
from collections import Counter
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from backend.app.taxonomy import Category

ML_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ML_DIR / "data" / "processed"
MODEL_DIR = ML_DIR / "models"
RESULTS_DIR = ML_DIR / "eval" / "results"

CATEGORY_ORDER = [c.value for c in Category]
FEATURE_COLUMNS = ["text", "txn_type", "channel"]
LOW_SUPPORT = 30
DIGIT_RUN = re.compile(r"\d{4,}")

VARIANTS = [
    ("text only", False, None),
    ("text + direction + channel", True, None),
    ("text + direction + channel + balanced weights", True, "balanced"),
]


def load(name: str) -> pd.DataFrame:
    df = pd.read_json(DATA_DIR / f"{name}.jsonl", lines=True, dtype=False, convert_dates=False)
    df["text"] = df["narration"].str.replace(DIGIT_RUN, "0", regex=True)
    return df


def make_pipeline(use_meta: bool, class_weight) -> Pipeline:
    text = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True, max_features=150_000
    )
    transformers = [("text", text, "text")]
    if use_meta:
        transformers.append(("meta", OneHotEncoder(handle_unknown="ignore"), ["txn_type", "channel"]))
    model = LogisticRegression(C=10, max_iter=300, class_weight=class_weight)
    return Pipeline([("features", ColumnTransformer(transformers)), ("model", model)])


def evaluate(pipe: Pipeline, df: pd.DataFrame) -> tuple[dict, list[str]]:
    pred = pipe.predict(df[FEATURE_COLUMNS])
    labels = sorted(set(df["category"]))
    scores = {
        "macro_f1": float(f1_score(df["category"], pred, labels=labels, average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(df["category"], pred)),
        "rows": len(df),
    }
    return scores, list(pred)


def per_category(df: pd.DataFrame, pred: list[str]) -> dict[str, tuple[int, float]]:
    _, _, f1, support = precision_recall_fscore_support(
        df["category"], pred, labels=CATEGORY_ORDER, zero_division=0
    )
    return {c: (int(n), float(f)) for c, f, n in zip(CATEGORY_ORDER, f1, support)}


def top_confusions(df: pd.DataFrame, pred: list[str], k: int = 8) -> list[tuple[str, str, int]]:
    errors = Counter((t, p) for t, p in zip(df["category"], pred) if t != p)
    return [(t, p, n) for (t, p), n in errors.most_common(k)]


def cell(n: int, f1: float) -> str:
    if n == 0:
        return f"{'-':>7} {'-':>8} "
    flag = "*" if n < LOW_SUPPORT else " "
    return f"{n:>7} {f1:>7.3f}{flag}"


if __name__ == "__main__":
    data = {name: load(name) for name in ("train", "val", "test_seen", "test_unseen")}
    train = data["train"]
    print(f"train rows: {len(train)} | test_seen: {len(data['test_seen'])} | test_unseen: {len(data['test_unseen'])}\n")

    results: dict[str, dict] = {}
    fitted: dict[str, tuple[Pipeline, dict[str, list[str]]]] = {}

    print(f"{'variant':<48} {'val F1':>7} {'seen F1':>8} {'unseen F1':>10} {'seen acc':>9} {'unseen acc':>11} {'sec':>5}")
    for name, use_meta, weight in VARIANTS:
        start = time.time()
        pipe = make_pipeline(use_meta, weight)
        pipe.fit(train[FEATURE_COLUMNS], train["category"])

        scores, preds = {}, {}
        for split in ("val", "test_seen", "test_unseen"):
            scores[split], preds[split] = evaluate(pipe, data[split])
        results[name] = scores
        fitted[name] = (pipe, preds)

        print(
            f"{name:<48} {scores['val']['macro_f1']:>7.3f} {scores['test_seen']['macro_f1']:>8.3f} "
            f"{scores['test_unseen']['macro_f1']:>10.3f} {scores['test_seen']['accuracy']:>9.3f} "
            f"{scores['test_unseen']['accuracy']:>11.3f} {time.time() - start:>5.0f}"
        )

    best = max(results, key=lambda n: results[n]["val"]["macro_f1"])
    pipe, preds = fitted[best]
    print(f"\nselected by validation macro-F1: {best}")

    seen = per_category(data["test_seen"], preds["test_seen"])
    unseen = per_category(data["test_unseen"], preds["test_unseen"])
    print(f"\n{'category':<18} {'seen n':>7} {'seen F1':>8}  {'unseen n':>8} {'unseen F1':>9}   (* = fewer than {LOW_SUPPORT} test rows)")
    for c in CATEGORY_ORDER:
        if seen[c][0] == 0 and unseen[c][0] == 0:
            continue
        print(f"{c:<18} {cell(*seen[c])} {cell(*unseen[c])}")

    confusions = {}
    for split in ("test_seen", "test_unseen"):
        confusions[split] = top_confusions(data[split], preds[split])
        print(f"\nmost common mistakes on {split} (true -> predicted : count)")
        for true, pred_label, n in confusions[split]:
            print(f"  {true:<18} -> {pred_label:<18} {n}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_DIR / "baseline_tfidf_lr.joblib")
    (RESULTS_DIR / "baseline.json").write_text(
        json.dumps(
            {
                "variants": results,
                "selected": best,
                "per_category": {c: {"seen": seen[c], "unseen": unseen[c]} for c in CATEGORY_ORDER},
                "top_confusions": confusions,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nsaved model to {MODEL_DIR} and metrics to {RESULTS_DIR / 'baseline.json'}")