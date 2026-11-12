import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

from backend.app.ingestion.extractor import extract_statement

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
DATE_FORMATS = ("%d/%m/%Y", "%d-%b-%Y", "%d %b %y")


def parse_date(text: str) -> str | None:
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def same(got: float | None, want: float | None) -> bool:
    if want is None:
        return got is None
    return got is not None and abs(got - want) < 0.005


pdfs = sorted(RAW_DIR.glob("stmt-*.pdf"))
if not pdfs:
    print("No PDFs found. Run: python -m ml.generator.render_pdf")
    sys.exit(1)

totals: Counter = Counter()
narration_problems: list[str] = []
other_problems: list[str] = []

for pdf in pdfs:
    truth = json.loads(pdf.with_suffix(".json").read_text(encoding="utf-8"))
    meta, rows = extract_statement(pdf)
    totals["joined"] += sum(r.joined_wrap for r in rows)
    expected = truth["transactions"]
    counts: Counter = Counter()

    for row, want in zip(rows, expected):
        is_debit = want["txn_type"] == "debit"
        checks = {
            "date": parse_date(row.date) == want["date"],
            "amount_side": same(row.debit, want["amount"] if is_debit else None)
            and same(row.credit, None if is_debit else want["amount"]),
            "balance": same(row.balance, want["balance"]),
            "narration": row.narration == want["narration"],
            "narration_nospace": row.narration.replace(" ", "") == want["narration"].replace(" ", ""),
        }
        for name, ok in checks.items():
            counts[name] += ok

        if not checks["narration"] and len(narration_problems) < 8:
            narration_problems.append(f"{pdf.stem} row {want['id']}\n   truth: {want['narration']}\n   got:   {row.narration}")
        for name in ("date", "amount_side", "balance"):
            if not checks[name] and len(other_problems) < 8:
                other_problems.append(f"{pdf.stem} row {want['id']} {name}: got {row.date} {row.debit} {row.credit} {row.balance} | want {want['date']} {want['amount']} {want['txn_type']} {want['balance']}")

    meta_ok = bool(
        meta.bank_name
        and meta.bank_name.lower() == truth["bank"].lower()
        and str(meta.period_start) == truth["period_start"]
        and str(meta.period_end) == truth["period_end"]
        and same(meta.opening_balance, truth["opening_balance"])
        and same(meta.closing_balance, truth["closing_balance"])
    )

    totals["rows_found"] += len(rows)
    totals["rows_expected"] += len(expected)
    totals["meta_ok"] += meta_ok
    for name, value in counts.items():
        totals[name] += value

    print(
        f"{pdf.stem} | {truth['layout']:<13} | rows {len(rows)}/{len(expected)} | date {counts['date']} | "
        f"amount+side {counts['amount_side']} | balance {counts['balance']} | "
        f"narration {counts['narration']} (ignoring spaces {counts['narration_nospace']}) | "
        f"meta {'ok' if meta_ok else 'MISMATCH'}"
    )

n = totals["rows_expected"]
print(f"\nTOTAL rows: found {totals['rows_found']} of {n}")
for name in ("date", "amount_side", "balance", "narration", "narration_nospace"):
    print(f"  {name:<18} {totals[name]:>5} / {n}  ({100 * totals[name] / n:.2f}%)")
print(f"  statements with correct meta: {totals['meta_ok']} / {len(pdfs)}")
print(f"  rows where a wrapped token was rejoined: {totals['joined']}")
if narration_problems:
    print("\nNarration mismatches (first few):")
    print("\n".join(narration_problems))
if other_problems:
    print("\nOther mismatches (first few):")
    print("\n".join(other_problems))