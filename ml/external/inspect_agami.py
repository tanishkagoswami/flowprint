import json
import re
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "ml" / "data" / "external" / "agami" / "train"

json_files = sorted(BASE.rglob("*.json"))
print("json files:", len(json_files))
print("statements per folder:", dict(Counter(p.parent.name for p in json_files)))

prefixes: Counter = Counter()
account_types: Counter = Counter()
total_txns = 0
failed = 0
both_sides = 0

for path in json_files:
    data = json.loads(path.read_text(encoding="utf-8"))
    account_types[data.get("account_type", "(missing)")] += 1
    for t in data.get("transactions", []):
        total_txns += 1
        failed += bool(t.get("failed"))
        both_sides += bool(t.get("debit")) and bool(t.get("credit"))
        words = re.findall(r"[A-Za-z]+", t.get("description") or "")
        prefixes[" ".join(words[:2]) or "(empty)"] += 1

print(f"\ntransactions: {total_txns} | failed flag set: {failed} | rows with both debit and credit: {both_sides}")
print("account types:", dict(account_types))
print("\ntop 15 narration prefixes:")
for prefix, count in prefixes.most_common(15):
    print(f"  {count:>6}  {prefix}")

print("\nOne sample statement per folder:")
for folder in sorted({p.parent for p in json_files}):
    path = sorted(folder.glob("*.json"))[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"\n[{folder.name}/{path.name}]")
    print("  top-level keys:", [k for k in data if k != "transactions"])
    print("  transaction keys:", list(data["transactions"][0].keys()))
    for t in data["transactions"][:6]:
        print(
            f"  {str(t.get('date'))[:10]} | {str(t.get('description'))[:58]:<58} "
            f"| dr {t.get('debit')} | cr {t.get('credit')} | bal {t.get('balance')}"
        )

print("\nCan pdfplumber read the sample PDFs?")
for pdf_path in sorted(BASE.rglob("*.pdf")):
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
        pages = len(pdf.pages)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    status = "TEXT LAYER" if len(text) > 50 else "NO TEXT (scan)"
    print(f"  {pdf_path.parent.name}/{pdf_path.name} | {pages} pages | {len(text)} chars | {status}")
    for ln in lines[:2]:
        print("      ", ln[:80])