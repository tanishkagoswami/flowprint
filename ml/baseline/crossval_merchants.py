import argparse
import json
import random
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from ml.baseline.build_dataset import FIRST_SEED, MIN_TRAIN_MERCHANTS, assign_statements
from ml.baseline.train_sklearn import DIGIT_RUN, FEATURE_COLUMNS, RESULTS_DIR, evaluate, make_pipeline
from ml.eval.stats import evaluate_with_ci, fmt, to_nature
from ml.generator.transactions import MERCHANTS, PERSONAS, generate_statement

VARIANTS = [("text only", False), ("text + direction + channel", True)]
OUT_PATH = RESULTS_DIR / "baseline_folds.json"


def assign_folds(n_folds: int, rng: random.Random) -> dict[str, int]:
    members: dict = defaultdict(set)
    categories_of: dict = defaultdict(set)
    for category, merchants in MERCHANTS.items():
        for name, _ in merchants:
            members[category].add(name)
            categories_of[name].add(category)

    names = sorted(categories_of)
    rng.shuffle(names)
    held = [defaultdict(int) for _ in range(n_folds)]
    load = [0] * n_folds
    fold_of: dict[str, int] = {}

    for name in names:
        options = [
            f
            for f in range(n_folds)
            if all(len(members[c]) - held[f][c] - 1 >= MIN_TRAIN_MERCHANTS for c in categories_of[name])
        ]
        if not options:
            continue
        fold = min(options, key=lambda f: (load[f], f))
        fold_of[name] = fold
        load[fold] += 1
        for c in categories_of[name]:
            held[fold][c] += 1
    return fold_of


def generate_rows(n_statements: int, split_seed: int) -> pd.DataFrame:
    rng = random.Random(split_seed)
    seeds_by_persona: dict = defaultdict(list)
    persona_of: dict[int, str] = {}
    for i in range(n_statements):
        persona = PERSONAS[i % len(PERSONAS)]
        seed = FIRST_SEED + i
        seeds_by_persona[persona].append(seed)
        persona_of[seed] = persona
    part_of = assign_statements(dict(seeds_by_persona), rng)

    rows = []
    for seed in sorted(part_of):
        statement = generate_statement(seed, persona_of[seed])
        for t in statement.transactions:
            rows.append(
                {
                    "statement_id": statement.statement_id,
                    "part": part_of[seed],
                    "narration": t["narration"],
                    "channel": t["channel"],
                    "txn_type": t["txn_type"],
                    "merchant": t["merchant"],
                    "category": t["category"],
                }
            )
    df = pd.DataFrame(rows)
    df["text"] = df["narration"].str.replace(DIGIT_RUN, "0", regex=True)
    return df


def point_scores(df: pd.DataFrame, pred: list[str]) -> tuple[float, float]:
    d = df.assign(pred=pred)
    category_f1 = f1_score(d["category"], d["pred"], labels=sorted(set(d["category"])), average="macro", zero_division=0)
    nature_true, nature_pred = to_nature(d["category"]), to_nature(d["pred"])
    nature_f1 = f1_score(nature_true, nature_pred, labels=sorted(set(nature_true)), average="macro", zero_division=0)
    return float(category_f1), float(nature_f1)


def merchant_table(pooled: pd.DataFrame) -> list[dict]:
    d = pooled.assign(correct=pooled["category"] == pooled["pred"])
    wrong = d[~d["correct"]].groupby("merchant")["pred"].agg(lambda s: s.value_counts().index[0])
    table = (
        d.groupby("merchant")
        .agg(rows=("correct", "size"), accuracy=("correct", "mean"), true_category=("category", lambda s: "/".join(sorted(set(s)))))
        .reset_index()
    )
    table["usually_predicted"] = table["merchant"].map(wrong).fillna("-")
    table["accuracy"] = table["accuracy"].astype(float)
    return table.sort_values(["accuracy", "rows"]).to_dict("records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--statements", type=int, default=400)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = generate_rows(args.statements, args.seed)
    fold_of = assign_folds(args.folds, random.Random(args.seed + 1))
    fold_members = {f: sorted(n for n, k in fold_of.items() if k == f) for f in range(args.folds)}
    all_brands = {name for merchants in MERCHANTS.values() for name, _ in merchants}

    print(f"rows: {len(df)} | statements: {df['statement_id'].nunique()} | brand merchants rotated through the unseen role: {len(fold_of)}")
    for f, names in fold_members.items():
        print(f"  fold {f} ({len(names)}): {', '.join(names)}")
    print("  never held out:", ", ".join(sorted(all_brands - set(fold_of))) or "none")

    summary: dict[str, dict] = {}
    pooled_by_variant: dict[str, pd.DataFrame] = {}

    for variant, use_meta in VARIANTS:
        print(f"\n== {variant} ==")
        print(f"{'fold':>4} {'merchants':>9} {'unseen rows':>11} {'val F1':>7} {'seen F1':>8} {'unseen F1':>10} {'nature F1':>10} {'unseen acc':>11}")
        folds, pooled = [], []

        for fold in range(args.folds):
            is_held = df["merchant"].isin(set(fold_members[fold]))
            train = df[(df["part"] == "train") & ~is_held]
            val = df[(df["part"] == "val") & ~is_held]
            seen = df[(df["part"] == "test") & ~is_held]
            unseen = df[(df["part"] == "test") & is_held]

            pipe = make_pipeline(use_meta, None)
            pipe.fit(train[FEATURE_COLUMNS], train["category"])

            val_scores, _ = evaluate(pipe, val)
            seen_scores, _ = evaluate(pipe, seen)
            unseen_scores, unseen_pred = evaluate(pipe, unseen)
            category_f1, nature_f1 = point_scores(unseen, unseen_pred)
            pooled.append(unseen.assign(pred=unseen_pred))

            record = {
                "fold": fold,
                "merchants": len(fold_members[fold]),
                "unseen_rows": len(unseen),
                "val_f1": val_scores["macro_f1"],
                "seen_f1": seen_scores["macro_f1"],
                "unseen_f1": category_f1,
                "unseen_nature_f1": nature_f1,
                "unseen_acc": unseen_scores["accuracy"],
            }
            folds.append(record)
            print(
                f"{fold:>4} {record['merchants']:>9} {record['unseen_rows']:>11} {record['val_f1']:>7.3f} "
                f"{record['seen_f1']:>8.3f} {record['unseen_f1']:>10.3f} {record['unseen_nature_f1']:>10.3f} {record['unseen_acc']:>11.3f}"
            )

        means = {}
        for key in ("val_f1", "seen_f1", "unseen_f1", "unseen_nature_f1", "unseen_acc"):
            values = [r[key] for r in folds]
            means[key] = (float(np.mean(values)), float(np.std(values, ddof=1)))
        print("mean +/- std across folds: " + " | ".join(f"{k} {m:.3f} +/- {s:.3f}" for k, (m, s) in means.items()))

        pooled_df = pd.concat(pooled)
        ci = {}
        for level in ("category", "nature"):
            ci[level] = evaluate_with_ci(pooled_df, level)
            r = ci[level]
            income = f" | income F1 {fmt(r['income_f1'])}" if r["income_f1"] else ""
            print(f"out-of-fold unseen, {level:<8} ({r['clusters']} merchants): macro-F1 {fmt(r['macro_f1'])} | accuracy {fmt(r['accuracy'])}{income}")

        summary[variant] = {"folds": folds, "means": means, "pooled_ci": ci}
        pooled_by_variant[variant] = pooled_df

    best = max(summary, key=lambda v: summary[v]["means"]["val_f1"][0])
    print(f"\nselected by mean validation macro-F1: {best}")

    table = merchant_table(pooled_by_variant[best])
    print(f"\nper-merchant accuracy on unseen rows ({best}), worst first")
    print(f"{'merchant':<22} {'rows':>6} {'acc':>6}  {'true category':<22} usually predicted instead")
    for r in table:
        print(f"{r['merchant']:<22} {r['rows']:>6} {r['accuracy']:>6.2f}  {r['true_category']:<22} {r['usually_predicted']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "seed": args.seed,
                "statements": args.statements,
                "n_folds": args.folds,
                "fold_of": fold_of,
                "selected": best,
                "variants": summary,
                "per_merchant": table,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nsaved {OUT_PATH}")