import datetime as dt
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .taxonomy import CATEGORY_INFO, Category, Channel, TxnType


class Tier(str, Enum):
    RULES = "rules"
    FUZZY = "fuzzy"
    RAG = "rag"
    LLM = "llm"
    REVIEW = "review"


class DecisionLabel(str, Enum):
    APPROVE = "approve"
    REVIEW = "review"
    DECLINE = "decline"


class RawRow(BaseModel):
    row_index: int
    date: str
    narration: str
    debit: float | None = None
    credit: float | None = None
    balance: float | None = None
    joined_wrap: bool = False


class StatementMeta(BaseModel):
    bank_name: str | None = None
    period_start: dt.date | None = None
    period_end: dt.date | None = None
    opening_balance: float | None = None
    closing_balance: float | None = None


class Transaction(BaseModel):
    id: int
    date: dt.date
    narration: str
    amount: float = Field(gt=0)
    txn_type: TxnType
    balance: float | None = None
    channel: Channel = Channel.OTHER


class LLMOutput(BaseModel):
    merchant: str
    category: Category


class ClassifiedTransaction(Transaction):
    merchant: str
    category: Category
    confidence: float = Field(ge=0, le=1)
    resolved_by: Tier
    needs_review: bool = False

    @model_validator(mode="after")
    def category_matches_direction(self):
        expected = CATEGORY_INFO[self.category].txn_type
        if expected != self.txn_type:
            raise ValueError(
                f"{self.category.value} is a {expected.value} category "
                f"but the transaction is a {self.txn_type.value}"
            )
        return self


class ReconciliationResult(BaseModel):
    passed: bool
    opening_balance: float | None = None
    closing_balance: float | None = None
    total_credits: float
    total_debits: float
    expected_closing: float | None = None
    difference: float | None = None
    balance_break_rows: list[int] = Field(default_factory=list)
    message: str


class MonthlySummary(BaseModel):
    month: str
    income: float
    expenses: float
    fixed_obligations: float
    net_cash_flow: float


class Metrics(BaseModel):
    months_analyzed: int
    avg_monthly_income: float
    avg_monthly_fixed_obligations: float
    avg_monthly_net_free_cash_flow: float
    dti_ratio: float
    income_volatility: float


class DecisionResult(BaseModel):
    decision: DecisionLabel
    reasons: list[str]
    metrics: Metrics
    monthly: list[MonthlySummary]


class StatementResult(BaseModel):
    statement_id: str
    filename: str
    meta: StatementMeta
    reconciliation: ReconciliationResult
    transactions: list[ClassifiedTransaction] = Field(default_factory=list)
    tier_counts: dict[Tier, int] = Field(default_factory=dict)
    decision: DecisionResult | None = None


if __name__ == "__main__":
    good = ClassifiedTransaction(
        id=1,
        date=dt.date(2026, 3, 1),
        narration="UPI/ZOMATO/1234",
        amount=349.0,
        txn_type=TxnType.DEBIT,
        channel=Channel.UPI,
        merchant="Zomato",
        category=Category.FOOD_DELIVERY,
        confidence=0.97,
        resolved_by=Tier.FUZZY,
    )
    print(good.model_dump_json(indent=2))

    try:
        ClassifiedTransaction(
            id=2,
            date=dt.date(2026, 3, 2),
            narration="UPI/ZOMATO/5678",
            amount=100.0,
            txn_type=TxnType.DEBIT,
            merchant="Zomato",
            category=Category.SALARY,
            confidence=0.9,
            resolved_by=Tier.LLM,
        )
    except ValueError as e:
        print("Rejected as expected:", e.errors()[0]["msg"])

    print("LLM must return:", LLMOutput.model_json_schema()["required"])