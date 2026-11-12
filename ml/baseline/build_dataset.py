import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from backend.app.taxonomy import Category
from ml.generator.transactions import MERCHANTS, PERSONAS, generate_statement

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
FIRST_SEED = 1000
SPLIT_FRACTIONS = {"train": 0.70, "val": 0.10}
MIN_TRAIN_MERCHANTS = 2
PARTITION = {"train": "train", "val": "val", "test_seen": "test", "test_unseen": "test"}


def choose_held_out(rng: random.Random) -> set[str]:
    names_by_category = {c: [name for name, _ in merchants] for c, merchants in MERCHANTS.items()}
    held: set[str] = set()

    for category in sorted(names_by_category, key=lambda c: c.value):
        names = sorted(names_by_category[category])
        if len(names) >= 3:
            held.add(rng.choice(names))

    for names in names_by_category.values():
        held_here = [n for n in names if n in held]
        while len(names) - len(held_here) < MIN_TRAIN_MERCHANTS and held_here:
            held.discard(held_here.pop())

    return held


def assign_statements(seeds_by_persona: dict[str, list[int]], rng: random.Random) -> dict[int, str]:
    assignment: dict[int, str] = {}
    for persona in sorted(seeds_by_persona):
        seeds = list(seeds_by_persona[persona])
        rng.shuffle(seeds)
        n_train = round(len(seeds) * SPLIT_FRACTIONS["train"])
        n_val = round(len(seeds) * SPLIT_FRACTIONS["val"])
        for i, seed in enumerate(seeds):
            if i < n_train:
                assignment[seed] = "train"
            elif i < n_train + n_val:
                assignment[seed] = "val"
            else:
                assignment[seed] = "test"
    return assignment


def build(n_statements: int, split_seed: int) -> tuple[dict[str, list[dict]], set[str]]:
    rng = random.Random(split_seed)
    held_out = choose_held_out(rng)

    seeds_by_persona: dict[str, list[int]] = defaultdict(list)
    persona_of: dict[int, str] = {}
    for i in range(n_statements):
        persona = PERSONAS[i % len(PERSONAS)]
        seeds_by_persona[persona].append(FIRST_SEED + i)
        persona_of[FIRST_SEED + i] = persona

    assignment = assign_statements(dict(seeds_by_persona), rng)
    splits: dict[str, list[dict]] = {name: [] for name in PARTITION}

    for seed in sorted(assignment):
        statement = generate_statement(seed, persona_of[seed])
        part = assignment[seed]
        for t in statement.transactions:
            row = {
                "statement_id": statement.statement_id,
                "persona": statement.persona,
                "row_id": t["id"],
                "date": t["date"],
                "narration": t["narration"],
                "channel": t["channel"],
                "txn_type": t["txn_type"],
                "amount": t["amount"],
                "merchant": t["merchant"],
                "category": t["category"],
            }
            is_held = t["merchant"] in held_out
            if part == "test":
                splits["test_unseen" if is_held else "test_seen"].append(row)
            elif not is_held:
                splits[part].append(row)

    return splits, held_out


def check_leaks(splits: dict[str, list[dict]], held_out: set[str]) -> None:
    partitions: dict[str, set[str]] = defaultdict(set)
    for name, rows in splits.items():
        for r in rows:
            partitions[r["statement_id"]].add(PARTITION[name])
    assert all(len(p) == 1 for p in partitions.values()), "a statement spans more than one split"

    for name in ("train", "val", "test_seen"):
        assert not any(r["merchant"] in held_out for r in splits[name]), f"held-out merchant leaked into {name}"
    assert all(r["merchant"] in held_out for r in splits["test_unseen"]), "seen merchant in test_unseen"


def summarize(splits: dict[str, list[dict]], held_out: set[str]) -> None:
    print("held-out merchants (only in test_unseen):", ", ".join(sorted(held_out)))
    print()
    for name, rows in splits.items():
        statements = len({r["statement_id"] for r in rows})
        print(f"{name:<12} {len(rows):>7} rows from {statements:>3} statements")

    counts = {name: Counter(r["category"] for r in rows) for name, rows in splits.items()}
    print(f"\n{'category':<18} {'train':>7} {'val':>6} {'test_seen':>10} {'test_unseen':>12}")
    for category in Category:
        c = category.value
        print(f"{c:<18} {counts['train'][c]:>7} {counts['val'][c]:>6} {counts['test_seen'][c]:>10} {counts['test_unseen'][c]:>12}")

    empty = [c.value for c in Category if counts["train"][c.value] == 0]
    if empty:
        print("\ncategories with zero training rows:", ", ".join(empty))
    sizes = [n for n in counts["train"].values() if n]
    print(f"largest / smallest class in train: {max(sizes)} / {min(sizes)} ({max(sizes) / min(sizes):.0f}x)")

    if splits["test_unseen"]:
        print("\nsample unseen-merchant rows:")
        for r in random.Random(0).sample(splits["test_unseen"], min(6, len(splits["test_unseen"]))):
            print(f"  {r['narration']:<42} | {r['merchant']:<18} | {r['category']}")


def write(splits: dict[str, list[dict]], held_out: set[str], n_statements: int, split_seed: int) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in splits.items():
        with (OUT_DIR / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    meta = {
        "statements": n_statements,
        "first_seed": FIRST_SEED,
        "split_seed": split_seed,
        "fractions": {"train": 0.70, "val": 0.10, "test": 0.20},
        "held_out_merchants": sorted(held_out),
        "rows": {name: len(rows) for name, rows in splits.items()},
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--statements", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    splits, held_out = build(args.statements, args.seed)
    check_leaks(splits, held_out)
    summarize(splits, held_out)
    write(splits, held_out, args.statements, args.seed)
    print(f"\nleak checks passed | wrote 4 files + meta.json to {OUT_DIR}")