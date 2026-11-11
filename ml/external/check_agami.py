import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "ml" / "data" / "external" / "agami" / "train"


def to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("+", "").strip())
    except ValueError:
        return None


def normalize(t):
    if "cr_dr" in t:
        amount = to_float(t.get("transaction_amount"))
        side = str(t.get("cr_dr") or "").strip().upper()[:1]
        if amount is None or side not in ("C", "D"):
            return None
        return ("credit" if side == "C" else "debit"), abs(amount)
    debit, credit = to_float(t.get("debit")), to_float(t.get("credit"))
    if debit and credit:
        return None
    if credit:
        return "credit", credit
    if debit:
        return "debit", debit
    return None


def fingerprint(data):
    text = "\n".join(str(t.get("description")) for t in data["transactions"])
    return hashlib.md5(text.encode("utf-8")).hexdigest()


folders = sorted(p.name for p in BASE.iterdir() if p.is_dir())
statements = {}
for folder in folders:
    for path in sorted((BASE / folder).glob("*.json")):
        statements[(folder, path.name)] = json.loads(path.read_text(encoding="utf-8"))

fp = {key: fingerprint(data) for key, data in statements.items()}
print(f"statements: {len(statements)} | unique by narration sequence: {len(set(fp.values()))}")

for a, b in [
    ("India_Bank_Statement_Digital_Type1", "India_Bank_Statement_Scanned_Type1"),
    ("India_Bank_Statement_Digital_Type2", "India_Bank_Statement_Scanned_Type2"),
    ("India_Bank_Statement_Digital_Type1", "India_Bank_Statement_Digital_Type2"),
]:
    names = [n for (f, n) in fp if f == a]
    same = sum(1 for n in names if fp.get((b, n)) == fp[(a, n)])
    print(f"{a[-13:]} vs {b[-13:]}: {same} of {len(names)} same-numbered files have identical narrations")

seen = set()
total_txns = unique_txns = 0
for key, data in statements.items():
    n = len(data["transactions"])
    total_txns += n
    if fp[key] not in seen:
        seen.add(fp[key])
        unique_txns += n
print(f"transactions: {total_txns} total | {unique_txns} after dropping duplicate statements")

type2 = next(data for (f, _), data in statements.items() if "Type2" in f)
print("\nType2 raw sample values:")
for t in type2["transactions"][:3]:
    print("  ", {k: t.get(k) for k in ("cr_dr", "transaction_amount", "available_balance", "failed")})

print("\nPer folder: reconciliation (opening + credits - debits = closing)")
for folder in folders:
    ok = bad = unparsed = 0
    sides = Counter()
    raw_cr_dr = Counter()
    for (f, _), data in statements.items():
        if f != folder:
            continue
        credits = debits = 0.0
        for t in data["transactions"]:
            if "cr_dr" in t:
                raw_cr_dr[str(t.get("cr_dr"))] += 1
            result = normalize(t)
            if result is None:
                unparsed += 1
                continue
            sides[result[0]] += 1
            if result[0] == "credit":
                credits += result[1]
            else:
                debits += result[1]
        opening = to_float(data.get("opening_balance"))
        closing = to_float(data.get("closing_balance"))
        if opening is None or closing is None or abs(opening + credits - debits - closing) >= 0.01:
            bad += 1
        else:
            ok += 1
    print(f"  {folder[-13:]}: reconciles {ok} | does not {bad} | unparsed rows {unparsed} | rows {dict(sides)}")
    if raw_cr_dr:
        print(f"     raw cr_dr values: {dict(raw_cr_dr)}")