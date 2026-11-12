import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from ..schemas import RawRow, StatementMeta

Y_TOL = 3.0
CELL_GAP = 5.0
ANCHOR_TOL = 2.5
CONTINUATION_GAP = 11.0
JOIN_TOL = 7.0
JOINED_KEY = "_joined"

HEADER_ROLES = {
    "date": "date",
    "txn date": "date",
    "value date": "value_date",
    "narration": "narration",
    "description": "narration",
    "particulars": "narration",
    "ref no": "ref",
    "debit": "debit",
    "withdrawals": "debit",
    "credit": "credit",
    "deposits": "credit",
    "amount": "amount",
    "dr/cr": "drcr",
    "balance": "balance",
}
RIGHT_ALIGNED = {"debit", "credit", "amount", "balance"}

AMOUNT_RE = re.compile(r"^\d[\d,]*\.\d{2}$")
DATE_RE = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[ -][A-Za-z]{3}[ -]\d{2,4})$")
PERIOD_RE = re.compile(r"Statement Period:\s*(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})", re.I)
OPENING_RE = re.compile(r"^(?:Opening Balance|Brought Forward|Balance at start of period):\s*([\d,]+\.\d{2})", re.I)
CLOSING_RE = re.compile(r"^(?:Closing Balance|Carried Forward|Balance at end of period):\s*([\d,]+\.\d{2})", re.I)


@dataclass
class Column:
    role: str
    anchor: float


def _num(text: str) -> float:
    return float(text.replace(",", ""))


def _to_date(text: str) -> dt.date:
    return dt.datetime.strptime(text, "%d/%m/%Y").date()


def _group_lines(words: list[dict]) -> list[list[dict]]:
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(word["top"] - lines[-1][0]["top"]) <= Y_TOL:
            lines[-1].append(word)
        else:
            lines.append([word])
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def _header_columns(line: list[dict]) -> list[Column] | None:
    cells: list[dict] = []
    for word in line:
        if cells and word["x0"] - cells[-1]["x1"] <= CELL_GAP:
            cells[-1]["text"] += " " + word["text"]
            cells[-1]["x1"] = word["x1"]
        else:
            cells.append({"text": word["text"], "x0": word["x0"], "x1": word["x1"]})

    columns = []
    for cell in cells:
        role = HEADER_ROLES.get(cell["text"].strip().lower())
        if role:
            columns.append(Column(role, cell["x1"] if role in RIGHT_ALIGNED else cell["x0"]))

    roles = {c.role for c in columns}
    if {"date", "narration", "balance"} <= roles:
        return columns
    return None


def _parse_line(line: list[dict], columns: list[Column]) -> tuple[dict[str, list[str]], float | None]:
    left = sorted((c for c in columns if c.role not in RIGHT_ALIGNED), key=lambda c: c.anchor)
    right = sorted((c for c in columns if c.role in RIGHT_ALIGNED), key=lambda c: c.anchor)
    cells: dict[str, list[str]] = {}
    edge: float | None = None

    for word in line:
        text = word["text"]

        if AMOUNT_RE.match(text):
            target = next((c for c in right if c.anchor >= word["x1"] - ANCHOR_TOL), None)
            if target:
                cells.setdefault(target.role, []).append(text)
                continue

        owner = None
        for column in left:
            if column.anchor <= word["x0"] + ANCHOR_TOL:
                owner = column
        if owner is None:
            continue
        if owner.role == "drcr" and abs(word["x0"] - owner.anchor) > ANCHOR_TOL:
            continue

        cells.setdefault(owner.role, []).append(text)
        if owner.role == "narration":
            edge = word["x1"] if edge is None else max(edge, word["x1"])

    return cells, edge


def _table_lines(page) -> list[tuple[str, dict[str, list[str]], float | None]]:
    columns = None
    accepted: list[tuple[str, dict[str, list[str]], float | None]] = []
    prev_top = 0.0

    for line in _group_lines(page.extract_words()):
        top = line[0]["top"]
        if columns is None:
            columns = _header_columns(line)
            continue

        cells, edge = _parse_line(line, columns)
        if "date" in cells and DATE_RE.match(" ".join(cells["date"])):
            accepted.append(("row", cells, edge))
        elif accepted and top - prev_top <= CONTINUATION_GAP and set(cells) == {"narration"}:
            accepted.append(("cont", cells, edge))
        else:
            continue
        prev_top = top

    return accepted


def _extract_page_rows(page) -> list[dict[str, list[str]]]:
    accepted = _table_lines(page)
    edges = [edge for _, _, edge in accepted if edge is not None]
    limit = max(edges) if edges else None

    rows: list[dict[str, list[str]]] = []
    prev_edge: float | None = None
    prev_words = 0

    for kind, cells, edge in accepted:
        words = len(cells.get("narration", []))
        if kind == "row":
            rows.append(cells)
        else:
            current = rows[-1].setdefault("narration", [])
            piece = cells["narration"]
            forced = (
                limit is not None
                and prev_edge is not None
                and prev_words == 1
                and prev_edge >= limit - JOIN_TOL
            )
            if forced and current:
                current[-1] += piece[0]
                current.extend(piece[1:])
                rows[-1][JOINED_KEY] = ["1"]
            else:
                current.extend(piece)
        prev_edge, prev_words = edge, words

    return rows


def _to_raw_row(index: int, cells: dict[str, list[str]]) -> RawRow:
    debit = _num(cells["debit"][0]) if "debit" in cells else None
    credit = _num(cells["credit"][0]) if "credit" in cells else None

    if "amount" in cells:
        amount = _num(cells["amount"][0])
        side = (cells.get("drcr") or [""])[0].lower()
        if side == "dr":
            debit = amount
        elif side == "cr":
            credit = amount

    return RawRow(
        row_index=index,
        date=" ".join(cells["date"]),
        narration=" ".join(cells.get("narration", [])),
        debit=debit,
        credit=credit,
        balance=_num(cells["balance"][0]) if "balance" in cells else None,
        joined_wrap=JOINED_KEY in cells,
    )


def _parse_meta(lines: list[str]) -> StatementMeta:
    meta: dict = {"bank_name": lines[0].strip() if lines else None}
    for line in lines:
        if (m := PERIOD_RE.search(line)) and "period_start" not in meta:
            meta["period_start"] = _to_date(m.group(1))
            meta["period_end"] = _to_date(m.group(2))
        elif (m := OPENING_RE.match(line)) and "opening_balance" not in meta:
            meta["opening_balance"] = _num(m.group(1))
        elif (m := CLOSING_RE.match(line)) and "closing_balance" not in meta:
            meta["closing_balance"] = _num(m.group(1))
    return StatementMeta(**meta)


def extract_statement(path: Path) -> tuple[StatementMeta, list[RawRow]]:
    text_lines: list[str] = []
    cell_rows: list[dict[str, list[str]]] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text_lines += (page.extract_text() or "").splitlines()
            cell_rows += _extract_page_rows(page)

    rows = [_to_raw_row(i, cells) for i, cells in enumerate(cell_rows, start=1)]
    return _parse_meta(text_lines), rows


if __name__ == "__main__":
    default = Path(__file__).resolve().parents[3] / "ml" / "data" / "raw" / "stmt-00001.pdf"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default

    meta, rows = extract_statement(path)
    print(path.name)
    print(meta.model_dump())
    print(f"rows extracted: {len(rows)}")
    for r in rows[:10]:
        print(f"{r.row_index:>3} | {r.date:<12} | {r.narration[:44]:<44} | dr {r.debit} | cr {r.credit} | bal {r.balance}")