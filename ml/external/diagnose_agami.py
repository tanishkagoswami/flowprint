import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "ml" / "data" / "external" / "agami" / "train"
FOLDERS = ["India_Bank_Statement_Digital_Type1", "India_Bank_Statement_Digital_Type2"]
TOL = 0.01


def to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("+", "").strip())
    except ValueError:
        return None


def read_row(t):
    if "cr_dr" in t:
        amount = to_float(t.get("transaction_amount"))
        side = str(t.get("cr_dr") or "").strip().upper()[:1]
        balance = to_float(t.get("available_balance"))
        if amount is None or side not in ("C", "D"):
            return None, balance
        return (abs(amount) if side == "C" else -abs(amount)), balance
    debit, credit = to_float(t.get("debit")), to_float(t.get("credit"))
    balance = to_float(t.get("balance"))
    if credit and not debit:
        return credit, balance
    if debit and not credit:
        return -debit, balance
    return None, balance


def describe(t):
    return str(t.get("description"))[:48]


for folder in FOLDERS:
    files = sorted((BASE / folder).glob("*.json"))
    clean = any_break = closing_bad = 0
    recon_all = recon_excl_failed = 0
    break_total = break_on_failed = break_at_first = 0
    unparsed_total = failed_total = 0
    break_samples, unparsed_samples = [], []

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        opening = to_float(data.get("opening_balance"))
        closing = to_float(data.get("closing_balance"))
        prev = opening
        total_all = total_ok = 0.0
        breaks = []

        for i, t in enumerate(data["transactions"]):
            failed = bool(t.get("failed"))
            failed_total += failed
            signed, bal = read_row(t)

            if signed is None:
                unparsed_total += 1
                delta = None if bal is None else round(bal - prev, 2)
                if len(unparsed_samples) < 5:
                    unparsed_samples.append(
                        (describe(t), t.get("debit"), t.get("credit"), failed, delta)
                    )
                if bal is not None:
                    prev = bal
                continue

            total_all += signed
            total_ok += 0 if failed else signed
            expected = prev + signed
            if bal is None:
                prev = expected
                continue
            if abs(expected - bal) >= TOL:
                breaks.append((i, round(bal - expected, 2), failed, describe(t), signed))
            prev = bal

        end_gap = None if closing is None else round(prev - closing, 2)
        closing_mismatch = end_gap is None or abs(end_gap) >= TOL
        closing_bad += closing_mismatch
        if breaks:
            any_break += 1
            if len(break_samples) < 4:
                break_samples.append((path.name, breaks[:2], end_gap))
        elif not closing_mismatch:
            clean += 1

        break_total += len(breaks)
        break_on_failed += sum(1 for b in breaks if b[2])
        break_at_first += sum(1 for b in breaks if b[0] == 0)
        if opening is not None and closing is not None:
            recon_all += abs(opening + total_all - closing) < TOL
            recon_excl_failed += abs(opening + total_ok - closing) < TOL

    print(f"\n=== {folder} ({len(files)} statements) ===")
    print(f"fully clean (no row breaks and closing matches): {clean}")
    print(f"statements with any row-level break: {any_break} | total breaks: {break_total} | on failed rows: {break_on_failed} | at first row: {break_at_first}")
    print(f"last row balance != closing_balance: {closing_bad}")
    print(f"opening + sum(all rows) = closing: {recon_all} | excluding failed rows: {recon_excl_failed}")
    print(f"failed rows: {failed_total} | rows with no usable amount: {unparsed_total}")

    for name, brk, end_gap in break_samples:
        print(f"  sample {name} (last balance minus closing = {end_gap})")
        for i, gap, failed, desc, signed in brk:
            print(f"     row {i} | gap {gap:,.2f} | failed={failed} | amount {signed:,.2f} | {desc}")

    if unparsed_samples:
        print("  rows with no usable amount (description | debit | credit | failed | balance change):")
        for sample in unparsed_samples:
            print("    ", sample)