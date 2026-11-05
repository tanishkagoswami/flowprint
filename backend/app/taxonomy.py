from dataclasses import dataclass
from enum import Enum


class TxnType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class Channel(str, Enum):
    UPI = "UPI"
    POS = "POS"
    NEFT = "NEFT"
    IMPS = "IMPS"
    RTGS = "RTGS"
    ACH = "ACH"
    ATM = "ATM"
    CHEQUE = "CHEQUE"
    OTHER = "OTHER"


class Nature(str, Enum):
    INCOME = "income"
    FIXED_OBLIGATION = "fixed_obligation"
    ESSENTIAL = "essential"
    DISCRETIONARY = "discretionary"
    NEUTRAL = "neutral"


class Category(str, Enum):
    SALARY = "salary"
    GIG_INCOME = "gig_income"
    BUSINESS_INCOME = "business_income"
    SELF_TRANSFER_IN = "self_transfer_in"
    LOAN_DISBURSAL = "loan_disbursal"
    REFUND = "refund"
    INTEREST = "interest"
    TRANSFER_IN = "transfer_in"
    OTHER_CREDIT = "other_credit"

    RENT = "rent"
    EMI_LOAN = "emi_loan"
    INSURANCE = "insurance"
    UTILITIES = "utilities"
    TELECOM = "telecom"
    GROCERIES = "groceries"
    FUEL = "fuel"
    TRANSPORT = "transport"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    FEES_CHARGES = "fees_charges"
    FOOD_DELIVERY = "food_delivery"
    DINING = "dining"
    SHOPPING = "shopping"
    SUBSCRIPTIONS = "subscriptions"
    CASH_WITHDRAWAL = "cash_withdrawal"
    INVESTMENTS = "investments"
    SELF_TRANSFER_OUT = "self_transfer_out"
    TRANSFER_OUT = "transfer_out"
    OTHER_DEBIT = "other_debit"


@dataclass(frozen=True)
class CategoryInfo:
    category: Category
    txn_type: TxnType
    nature: Nature
    description: str


_C = TxnType.CREDIT
_D = TxnType.DEBIT

CATEGORY_INFO: dict[Category, CategoryInfo] = {
    info.category: info
    for info in [
        CategoryInfo(Category.SALARY, _C, Nature.INCOME, "Regular employer salary credit"),
        CategoryInfo(Category.GIG_INCOME, _C, Nature.INCOME, "Platform payouts for gig and freelance work"),
        CategoryInfo(Category.BUSINESS_INCOME, _C, Nature.INCOME, "Customer payments received by a small business"),
        CategoryInfo(Category.SELF_TRANSFER_IN, _C, Nature.NEUTRAL, "Money moved in from the applicant's own other account"),
        CategoryInfo(Category.LOAN_DISBURSAL, _C, Nature.NEUTRAL, "Loan amount credited by a lender, not income"),
        CategoryInfo(Category.REFUND, _C, Nature.NEUTRAL, "Reversal or refund of an earlier payment"),
        CategoryInfo(Category.INTEREST, _C, Nature.NEUTRAL, "Bank interest credit"),
        CategoryInfo(Category.TRANSFER_IN, _C, Nature.NEUTRAL, "Credit from an individual, purpose unclear"),
        CategoryInfo(Category.OTHER_CREDIT, _C, Nature.NEUTRAL, "Credit that fits no other category"),

        CategoryInfo(Category.RENT, _D, Nature.FIXED_OBLIGATION, "Monthly house or shop rent"),
        CategoryInfo(Category.EMI_LOAN, _D, Nature.FIXED_OBLIGATION, "Loan or credit card repayment"),
        CategoryInfo(Category.INSURANCE, _D, Nature.FIXED_OBLIGATION, "Insurance premiums"),
        CategoryInfo(Category.UTILITIES, _D, Nature.ESSENTIAL, "Electricity, water, gas, broadband"),
        CategoryInfo(Category.TELECOM, _D, Nature.ESSENTIAL, "Mobile recharge and postpaid bills"),
        CategoryInfo(Category.GROCERIES, _D, Nature.ESSENTIAL, "Supermarkets and grocery stores"),
        CategoryInfo(Category.FUEL, _D, Nature.ESSENTIAL, "Petrol, diesel, CNG"),
        CategoryInfo(Category.TRANSPORT, _D, Nature.ESSENTIAL, "Metro, bus, cabs, tolls"),
        CategoryInfo(Category.HEALTHCARE, _D, Nature.ESSENTIAL, "Hospitals, pharmacies, diagnostics"),
        CategoryInfo(Category.EDUCATION, _D, Nature.ESSENTIAL, "Fees and course payments"),
        CategoryInfo(Category.FEES_CHARGES, _D, Nature.ESSENTIAL, "Bank charges, penalties, GST on charges"),
        CategoryInfo(Category.FOOD_DELIVERY, _D, Nature.DISCRETIONARY, "Food delivery apps"),
        CategoryInfo(Category.DINING, _D, Nature.DISCRETIONARY, "Restaurants and cafes"),
        CategoryInfo(Category.SHOPPING, _D, Nature.DISCRETIONARY, "Online and offline retail"),
        CategoryInfo(Category.SUBSCRIPTIONS, _D, Nature.DISCRETIONARY, "Streaming, apps, memberships"),
        CategoryInfo(Category.CASH_WITHDRAWAL, _D, Nature.DISCRETIONARY, "ATM cash withdrawals, end use unknown"),
        CategoryInfo(Category.INVESTMENTS, _D, Nature.NEUTRAL, "Mutual funds, stocks, SIPs"),
        CategoryInfo(Category.SELF_TRANSFER_OUT, _D, Nature.NEUTRAL, "Money moved to the applicant's own other account"),
        CategoryInfo(Category.TRANSFER_OUT, _D, Nature.NEUTRAL, "Payment to an individual, purpose unclear"),
        CategoryInfo(Category.OTHER_DEBIT, _D, Nature.DISCRETIONARY, "Debit that fits no other category"),
    ]
}


def categories_for(txn_type: TxnType) -> list[Category]:
    return [c for c, info in CATEGORY_INFO.items() if info.txn_type == txn_type]


def counts_as_income(category: Category) -> bool:
    return CATEGORY_INFO[category].nature == Nature.INCOME


def is_fixed_obligation(category: Category) -> bool:
    return CATEGORY_INFO[category].nature == Nature.FIXED_OBLIGATION


if __name__ == "__main__":
    missing = [c for c in Category if c not in CATEGORY_INFO]
    assert not missing, f"Categories without info: {missing}"

    print(f"Total categories: {len(Category)}")
    print(f"Credit categories: {len(categories_for(TxnType.CREDIT))}")
    print(f"Debit categories: {len(categories_for(TxnType.DEBIT))}")
    print("Income categories:", [c.value for c in Category if counts_as_income(c)])
    print("Fixed obligations:", [c.value for c in Category if is_fixed_obligation(c)])