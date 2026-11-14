import joblib
import numpy as np
import pandas as pd

from backend.app.taxonomy import CATEGORY_INFO, Category
from ml.baseline.train_sklearn import FEATURE_COLUMNS, MODEL_DIR, load


def to_nature(categories: pd.Series) -> pd.Series:
    return categories.map(lambda c: CATEGORY_INFO[Category(c)].nature.value)


def cluster_confusions(df: pd.DataFrame, true_col: str, pred_col: str, cluster_col: str):
    labels = sorted(set(df[true_col]) | set(df[pred_col]))
    label_index = {label: i for i, label in enumerate(labels)}
    cluster_index = {key: i for i, key in enumerate(sorted(df[cluster_col].unique()))}

    stack = np.zeros((len(cluster_index), len(labels), len(labels)))
    true = df[true_col].map(label_index).to_numpy()
    pred = df[pred_col].map(label_index).to_numpy()
    cluster = df[cluster_col].map(cluster_index).to_numpy()
    np.add.at(stack, (cluster, true, pred), 1)
    return stack, labels


def macro_f1(M: np.ndarray) -> float:
    tp = np.diag(M)
    denom = 2 * tp + (M.sum(axis=0) - tp) + (M.sum(axis=1) - tp)
    f1 = np.divide(2 * tp, denom, out=np.zeros_like(tp), where=denom > 0)
    present = M.sum(axis=1) > 0
    return float(f1[present].mean())


def accuracy(M: np.ndarray) -> float:
    return float(np.trace(M) / M.sum())


def class_f1(labels: list[str], name: str):
    k = labels.index(name)

    def metric(M: np.ndarray) -> float:
        if M[k, :].sum() == 0:
            return float("nan")
        tp = M[k, k]
        denom = 2 * tp + (M[:, k].sum() - tp) + (M[k, :].sum() - tp)
        return float(2 * tp / denom) if denom > 0 else float("nan")

    return metric


def bootstrap(stack: np.ndarray, metric, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    n, size, _ = stack.shape
    flat = stack.reshape(n, size * size)
    point = metric(stack.sum(axis=0))

    draws = []
    for _ in range(n_boot):
        weights = np.bincount(rng.integers(0, n, n), minlength=n)
        draws.append(metric((weights @ flat).reshape(size, size)))

    low, high = np.nanpercentile(draws, [2.5, 97.5])
    return point, float(low), float(high)


def fmt(result: tuple[float, float, float] | None) -> str:
    if result is None:
        return "-"
    point, low, high = result
    return f"{point:.3f} [{low:.3f}, {high:.3f}]"


def evaluate_with_ci(df: pd.DataFrame, level: str = "category", cluster_col: str = "merchant") -> dict:
    d = df
    if level == "nature":
        d = df.assign(category=to_nature(df["category"]), pred=to_nature(df["pred"]))

    stack, labels = cluster_confusions(d, "category", "pred", cluster_col)
    out = {
        "clusters": stack.shape[0],
        "macro_f1": bootstrap(stack, macro_f1),
        "accuracy": bootstrap(stack, accuracy),
        "income_f1": None,
    }
    if level == "nature" and "income" in labels:
        out["income_f1"] = bootstrap(stack, class_f1(labels, "income"))
    return out


if __name__ == "__main__":
    pipe = joblib.load(MODEL_DIR / "baseline_tfidf_lr.joblib")

    print(f"{'level':<9} {'split':<12} {'merchants':>9}  {'macro-F1 [95% CI]':<24} {'accuracy [95% CI]':<24} {'income F1 [95% CI]':<24}")
    for split in ("test_seen", "test_unseen"):
        df = load(split)
        df["pred"] = pipe.predict(df[FEATURE_COLUMNS])
        for level in ("category", "nature"):
            r = evaluate_with_ci(df, level)
            print(
                f"{level:<9} {split:<12} {r['clusters']:>9}  {fmt(r['macro_f1']):<24} "
                f"{fmt(r['accuracy']):<24} {fmt(r['income_f1']):<24}"
            )