import calendar
import datetime as dt
import random
import string
from collections import Counter
from dataclasses import asdict, dataclass

from backend.app.taxonomy import CATEGORY_INFO, Category, Channel, TxnType

PERSONAS = ("salaried", "gig", "business")

FIRST_NAMES = ["Aarav", "Ananya", "Rohit", "Priya", "Kiran", "Sneha", "Vikram", "Meera", "Arjun", "Divya", "Suresh", "Lakshmi"]
LAST_NAMES = ["Sharma", "Reddy", "Patel", "Nair", "Singh", "Iyer", "Gupta", "Naidu", "Das", "Rao"]
BANKS = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank"]
BANK_CODES = ["HDFC", "ICIC", "SBIN", "UTIB", "KKBK", "YESB"]
FEE_NARRATIONS = ["SMS CHARGES", "ATM ANNUAL FEE", "GST ON CHARGES", "MIN BAL PENALTY", "DEBIT CARD AMC"]
FEE_AMOUNTS = [17.70, 23.60, 59.00, 118.00, 177.00, 354.00]
ATM_LOCATIONS = ["MG ROAD BANGALORE", "ANNA NAGAR CHENNAI", "CONNAUGHT PLACE DELHI", "ANDHERI WEST MUMBAI", "KUKATPALLY HYDERABAD"]

MERCHANTS: dict[Category, list[tuple[str, list[str]]]] = {
    Category.SALARY: [
        ("TCS", ["TCS", "TATA CONSULTANCY SERV"]),
        ("Infosys", ["INFOSYS LTD", "INFOSYS"]),
        ("Wipro", ["WIPRO LTD", "WIPRO"]),
        ("Cognizant", ["COGNIZANT TECH", "COGNIZANT"]),
        ("Accenture", ["ACCENTURE SOL", "ACCENTURE"]),
        ("Zoho", ["ZOHO CORP", "ZOHO"]),
    ],
    Category.GIG_INCOME: [
        ("Uber", ["UBER INDIA", "UBER*TRIP"]),
        ("Swiggy", ["SWIGGY", "BUNDL TECH"]),
        ("Zomato", ["ZOMATO", "ZOMATO PAYOUT"]),
        ("Urban Company", ["URBANCLAP", "URBAN COMPANY"]),
        ("Porter", ["PORTER", "SMARTSHIFT LOGISTICS"]),
        ("Rapido", ["RAPIDO", "ROPPEN TRANSPORTATION"]),
    ],
    Category.LOAN_DISBURSAL: [
        ("Bajaj Finance", ["BAJAJ FINANCE LOAN DISB", "BAJAJFIN DISBURSAL"]),
        ("Moneyview", ["MONEYVIEW LOAN", "MONEYVIEW DISB"]),
        ("KreditBee", ["KREDITBEE LOAN", "KREDITBEE DISBURSE"]),
        ("Navi", ["NAVI FINSERV LOAN", "NAVI DISB"]),
    ],
    Category.REFUND: [
        ("Amazon", ["AMAZON REFUND", "AMAZON PAY REV"]),
        ("Flipkart", ["FLIPKART REFUND", "FLIPKART REV"]),
        ("Swiggy", ["SWIGGY REFUND", "SWIGGY REV"]),
        ("Myntra", ["MYNTRA REFUND", "MYNTRA REV"]),
    ],
    Category.EMI_LOAN: [
        ("HDFC Bank Loan", ["HDFC BANK LTD EMI", "HDFC LOAN EMI"]),
        ("ICICI Bank Loan", ["ICICI BANK EMI", "ICICI LOAN"]),
        ("Bajaj Finance", ["BAJAJ FINANCE", "BAJAJFIN EMI"]),
        ("Tata Capital", ["TATA CAPITAL", "TATACAP EMI"]),
        ("Credit Card Payment", ["CC PAYMENT", "CREDIT CARD BILL"]),
    ],
    Category.INSURANCE: [
        ("LIC", ["LIC OF INDIA", "LIC PREMIUM"]),
        ("HDFC Life", ["HDFC LIFE", "HDFCLIFE PREM"]),
        ("ICICI Prudential", ["ICICI PRU LIFE", "ICICIPRU PREMIUM"]),
        ("Star Health", ["STAR HEALTH", "STARHEALTH INS"]),
    ],
    Category.UTILITIES: [
        ("APSPDCL", ["APSPDCL", "APSPDCL BILL"]),
        ("BESCOM", ["BESCOM", "BESCOM ELECTRICITY"]),
        ("TSSPDCL", ["TSSPDCL", "TSSPDCL BILL"]),
        ("ACT Fibernet", ["ACT FIBERNET", "ACT BROADBAND"]),
        ("Airtel Xstream", ["AIRTEL XSTREAM", "AIRTEL BROADBAND"]),
    ],
    Category.TELECOM: [
        ("Jio", ["JIO", "RELIANCE JIO", "JIO PREPAID"]),
        ("Airtel", ["AIRTEL", "BHARTI AIRTEL", "AIRTEL RECHARGE"]),
        ("Vi", ["VODAFONE IDEA", "VI PREPAID"]),
    ],
    Category.GROCERIES: [
        ("Reliance Smart", ["RELI*SUPER", "RELIANCE SMART", "RELIANCESMART"]),
        ("DMart", ["DMART", "AVENUE SUPERMARTS", "AVENUE SUPERMT"]),
        ("BigBasket", ["BIGBASKET", "BB*GROCERY", "INNOVATIVE RETAIL"]),
        ("More Retail", ["MORE RETAIL", "MORE*SUPERMKT"]),
    ],
    Category.FUEL: [
        ("Indian Oil", ["INDIAN OIL", "IOCL PETROL", "INDIANOIL"]),
        ("HPCL", ["HPCL", "HINDUSTAN PETROLEUM"]),
        ("BPCL", ["BPCL", "BHARAT PETROLEUM"]),
        ("Shell", ["SHELL PETROL", "SHELL INDIA"]),
    ],
    Category.TRANSPORT: [
        ("Uber", ["UBER INDIA", "UBER*TRIP"]),
        ("Ola", ["OLA CABS", "ANI TECHNOLOGIES"]),
        ("Rapido", ["RAPIDO", "ROPPEN TRANSPORTATION"]),
        ("FASTag", ["FASTAG RECHARGE", "NETC FASTAG"]),
        ("Metro", ["METRO RAIL", "METRO CARD"]),
    ],
    Category.HEALTHCARE: [
        ("Apollo Pharmacy", ["APOLLO PHARMACY", "APOLLO PHARM"]),
        ("MedPlus", ["MEDPLUS", "MEDPLUS HEALTH"]),
        ("1mg", ["1MG", "TATA 1MG"]),
        ("Apollo Hospitals", ["APOLLO HOSPITALS", "APOLLO HOSP"]),
    ],
    Category.EDUCATION: [
        ("Udemy", ["UDEMY", "UDEMY INDIA"]),
        ("Coursera", ["COURSERA", "COURSERA INC"]),
        ("BYJU'S", ["BYJUS", "THINK AND LEARN"]),
        ("College Fee", ["COLLEGE FEE", "UNIVERSITY FEE"]),
    ],
    Category.FOOD_DELIVERY: [
        ("Swiggy", ["SWIGGY", "BUNDL TECH", "SWIGGY*ORDER"]),
        ("Zomato", ["ZOMATO", "ZOMATO*ORDER"]),
    ],
    Category.DINING: [
        ("Domino's", ["DOMINOS", "JUBILANT FOODWORKS"]),
        ("McDonald's", ["MCDONALDS", "WESTLIFE DEV"]),
        ("Barbeque Nation", ["BARBEQUE NATION", "BBQ NATION"]),
        ("Chai Point", ["CHAI POINT", "CHAIPOINT"]),
        ("Starbucks", ["STARBUCKS", "TATA STARBUCKS"]),
    ],
    Category.SHOPPING: [
        ("Amazon", ["AMAZON", "AMAZON PAY", "AMZN*MKTP"]),
        ("Flipkart", ["FLIPKART", "FLIPKART INTERNET"]),
        ("Myntra", ["MYNTRA", "MYNTRA DESIGNS"]),
        ("Ajio", ["AJIO", "AJIO RELIANCE"]),
        ("Decathlon", ["DECATHLON", "DECATHLON SPORTS"]),
    ],
    Category.SUBSCRIPTIONS: [
        ("Netflix", ["NETFLIX", "NETFLIX.COM"]),
        ("Spotify", ["SPOTIFY", "SPOTIFY INDIA"]),
        ("YouTube Premium", ["GOOGLE*YOUTUBE", "YOUTUBEPREMIUM"]),
        ("Hotstar", ["HOTSTAR", "DISNEY HOTSTAR"]),
        ("Adobe", ["ADOBE SYSTEMS", "ADOBE"]),
    ],
    Category.INVESTMENTS: [
        ("Zerodha", ["ZERODHA", "ZERODHA BROKING"]),
        ("Groww", ["GROWW", "BILLIONBRAINS GARAGE"]),
        ("ICICI Prudential MF", ["ICICI PRU MF", "ICICIPRUMF SIP"]),
    ],
}

PERSON_CATEGORIES = {Category.RENT, Category.TRANSFER_IN, Category.TRANSFER_OUT, Category.BUSINESS_INCOME}

CHANNEL_CHOICES: dict[Category, list[Channel]] = {
    Category.SALARY: [Channel.NEFT, Channel.NEFT, Channel.IMPS, Channel.ACH],
    Category.GIG_INCOME: [Channel.UPI, Channel.IMPS, Channel.NEFT],
    Category.BUSINESS_INCOME: [Channel.UPI, Channel.UPI, Channel.UPI, Channel.IMPS, Channel.NEFT],
    Category.SELF_TRANSFER_IN: [Channel.UPI, Channel.IMPS, Channel.NEFT],
    Category.SELF_TRANSFER_OUT: [Channel.UPI, Channel.IMPS, Channel.NEFT],
    Category.LOAN_DISBURSAL: [Channel.IMPS, Channel.NEFT],
    Category.REFUND: [Channel.UPI, Channel.IMPS],
    Category.INTEREST: [Channel.OTHER],
    Category.TRANSFER_IN: [Channel.UPI, Channel.UPI, Channel.IMPS],
    Category.RENT: [Channel.UPI, Channel.NEFT, Channel.IMPS],
    Category.EMI_LOAN: [Channel.ACH, Channel.ACH, Channel.ACH, Channel.NEFT],
    Category.INSURANCE: [Channel.ACH, Channel.ACH, Channel.UPI],
    Category.UTILITIES: [Channel.UPI, Channel.UPI, Channel.ACH],
    Category.TELECOM: [Channel.UPI, Channel.UPI, Channel.ACH],
    Category.GROCERIES: [Channel.POS, Channel.UPI, Channel.UPI],
    Category.FUEL: [Channel.POS, Channel.UPI],
    Category.TRANSPORT: [Channel.UPI, Channel.UPI, Channel.POS],
    Category.HEALTHCARE: [Channel.UPI, Channel.POS],
    Category.EDUCATION: [Channel.UPI, Channel.NEFT, Channel.POS],
    Category.FEES_CHARGES: [Channel.OTHER],
    Category.FOOD_DELIVERY: [Channel.UPI, Channel.UPI, Channel.POS],
    Category.DINING: [Channel.POS, Channel.UPI, Channel.UPI],
    Category.SHOPPING: [Channel.UPI, Channel.POS, Channel.POS],
    Category.SUBSCRIPTIONS: [Channel.ACH, Channel.POS],
    Category.CASH_WITHDRAWAL: [Channel.ATM],
    Category.INVESTMENTS: [Channel.ACH, Channel.UPI],
    Category.TRANSFER_OUT: [Channel.UPI, Channel.UPI, Channel.IMPS],
}

VARIABLE_SPENDING = [
    (Category.GROCERIES, (6, 12), (150, 2800)),
    (Category.FUEL, (2, 6), (300, 1800)),
    (Category.TRANSPORT, (3, 10), (40, 650)),
    (Category.FOOD_DELIVERY, (2, 10), (120, 900)),
    (Category.DINING, (1, 5), (200, 2200)),
    (Category.SHOPPING, (1, 5), (300, 5000)),
    (Category.SUBSCRIPTIONS, (1, 3), (149, 799)),
    (Category.HEALTHCARE, (0, 2), (150, 3500)),
    (Category.EDUCATION, (0, 1), (500, 6000)),
    (Category.CASH_WITHDRAWAL, (0, 3), (500, 5000)),
    (Category.TRANSFER_OUT, (1, 4), (200, 5000)),
]


@dataclass
class Profile:
    persona: str
    monthly_income: float
    rent: float
    rent_day: int
    emi: float | None
    emi_day: int
    insurance: float | None
    sip: float | None
    sip_day: int
    salary_day: int
    fixed: dict[Category, tuple[str, str]]


@dataclass
class SyntheticStatement:
    statement_id: str
    persona: str
    holder: str
    bank: str
    period_start: dt.date
    period_end: dt.date
    opening_balance: float
    closing_balance: float
    transactions: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def _person(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _date(year: int, month: int, day: int) -> dt.date:
    return dt.date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _money(rng: random.Random, value: float) -> float:
    value = max(value, 1.0)
    return float(round(value)) if rng.random() < 0.8 else round(value, 2)


def _pick(rng: random.Random, category: Category) -> tuple[str, str]:
    name, fragments = rng.choice(MERCHANTS[category])
    return name, rng.choice(fragments)


def _build_profile(rng: random.Random, persona: str) -> Profile:
    if persona == "salaried":
        income = round(rng.uniform(25000, 120000) / 500) * 500
    elif persona == "gig":
        income = round(rng.uniform(18000, 45000) / 500) * 500
    else:
        income = round(rng.uniform(60000, 250000) / 1000) * 1000

    landlord = _person(rng)
    fixed: dict[Category, tuple[str, str]] = {
        Category.RENT: (landlord, f"{landlord} RENT" if rng.random() < 0.5 else landlord),
        Category.EMI_LOAN: _pick(rng, Category.EMI_LOAN),
        Category.INSURANCE: _pick(rng, Category.INSURANCE),
        Category.INVESTMENTS: _pick(rng, Category.INVESTMENTS),
    }
    if persona == "salaried":
        employer, fragment = _pick(rng, Category.SALARY)
        fixed[Category.SALARY] = (employer, f"{fragment} SALARY")

    return Profile(
        persona=persona,
        monthly_income=float(income),
        rent=float(round(income * rng.uniform(0.15, 0.30), -2)),
        rent_day=rng.randint(1, 7),
        emi=float(round(income * rng.uniform(0.08, 0.30), -2)) if rng.random() < 0.6 else None,
        emi_day=rng.randint(3, 10),
        insurance=rng.choice([None, 3500.0, 6000.0, 9000.0]),
        sip=rng.choice([None, 1000.0, 2000.0, 5000.0]),
        sip_day=rng.randint(5, 12),
        salary_day=rng.randint(1, 5),
        fixed=fixed,
    )


def _month_events(rng: random.Random, p: Profile, year: int, month: int) -> list[tuple[dt.date, Category, float]]:
    events: list[tuple[dt.date, Category, float]] = []

    def add(day: int, category: Category, amount: float) -> None:
        events.append((_date(year, month, day), category, _money(rng, amount)))

    income = p.monthly_income

    if p.persona == "salaried":
        add(p.salary_day, Category.SALARY, income)
    else:
        count = rng.randint(10, 22) if p.persona == "gig" else rng.randint(18, 40)
        category = Category.GIG_INCOME if p.persona == "gig" else Category.BUSINESS_INCOME
        total = income * (rng.uniform(0.7, 1.25) if p.persona == "gig" else rng.uniform(0.6, 1.4))
        parts = [rng.uniform(0.5, 1.5) for _ in range(count)]
        for part in parts:
            add(rng.randint(1, 28), category, total * part / sum(parts))

    add(p.rent_day, Category.RENT, p.rent)
    if p.emi:
        add(p.emi_day, Category.EMI_LOAN, p.emi)
    if p.insurance and month % 3 == 1:
        add(rng.randint(8, 15), Category.INSURANCE, p.insurance)
    if p.sip:
        add(p.sip_day, Category.INVESTMENTS, p.sip)

    add(rng.randint(8, 16), Category.UTILITIES, rng.uniform(700, 3200))
    if rng.random() < 0.6:
        add(rng.randint(10, 20), Category.UTILITIES, rng.choice([499, 649, 799, 1099]))
    add(rng.randint(2, 6), Category.TELECOM, rng.choice([299, 399, 599, 719, 999]))

    scale = min(max(income / 50000, 0.6), 1.8)
    for category, (low_n, high_n), (low_amt, high_amt) in VARIABLE_SPENDING:
        for _ in range(rng.randint(low_n, high_n)):
            add(rng.randint(1, 28), category, rng.uniform(low_amt, high_amt) * scale)

    if rng.random() < 0.5:
        add(rng.randint(1, 28), Category.SELF_TRANSFER_IN, rng.uniform(2000, 15000))
    if rng.random() < 0.4:
        add(rng.randint(1, 28), Category.SELF_TRANSFER_OUT, rng.uniform(2000, 15000))
    if rng.random() < 0.06:
        add(rng.randint(1, 28), Category.LOAN_DISBURSAL, rng.uniform(20000, 80000))
    if rng.random() < 0.3:
        add(rng.randint(1, 28), Category.REFUND, rng.uniform(150, 2500))
    if rng.random() < 0.3:
        add(rng.randint(1, 28), Category.TRANSFER_IN, rng.uniform(500, 5000))
    if rng.random() < 0.5:
        add(rng.randint(1, 28), Category.FEES_CHARGES, rng.choice(FEE_AMOUNTS))
    if month % 3 == 0:
        add(28, Category.INTEREST, rng.uniform(50, 400))

    return events


def _counterparty(rng: random.Random, p: Profile, category: Category, holder: str) -> tuple[str, str]:
    if category in p.fixed:
        return p.fixed[category]
    if category in PERSON_CATEGORIES:
        name = _person(rng)
        return name, name
    if category in (Category.SELF_TRANSFER_IN, Category.SELF_TRANSFER_OUT):
        return "Self Transfer", holder
    if category == Category.FEES_CHARGES:
        return "Bank Charges", rng.choice(FEE_NARRATIONS)
    if category == Category.CASH_WITHDRAWAL:
        return "ATM Withdrawal", rng.choice(ATM_LOCATIONS)
    if category == Category.INTEREST:
        return "Bank Interest", "INT.PD"
    return _pick(rng, category)


def _noise(rng: random.Random, text: str) -> str:
    text = text.upper()
    if rng.random() < 0.2:
        text = text.replace("/", " ")
    if rng.random() < 0.3 and len(text) > 26:
        text = text[: rng.randint(24, min(len(text), 34))]
    return " ".join(text.split())


def _narrate(rng: random.Random, channel: Channel, fragment: str, is_debit: bool) -> str:
    ref = "".join(rng.choices(string.digits, k=rng.choice([10, 12])))
    if channel == Channel.UPI:
        side = "DR" if is_debit else "CR"
        text = rng.choice([
            f"UPI/{fragment}/{ref}",
            f"UPI/{side}/{ref}/{fragment}/{rng.choice(BANK_CODES)}",
            f"UPI-{fragment}-{ref}",
        ])
    elif channel == Channel.POS:
        text = f"POS*{fragment}*{rng.randint(100, 999)}"
    elif channel == Channel.ACH:
        text = rng.choice([
            f"ACH*{fragment}*PAY",
            f"ACH {'D' if is_debit else 'C'}- {fragment}-{ref[:8]}",
        ])
    elif channel == Channel.NEFT:
        text = f"NEFT-{ref}-{fragment}"
    elif channel == Channel.IMPS:
        text = f"IMPS/{ref}/{fragment}"
    elif channel == Channel.ATM:
        text = f"ATM WDL {fragment} {ref[:6]}"
    else:
        text = fragment
    return _noise(rng, text)


def generate_statement(
    seed: int,
    persona: str = "salaried",
    months: int = 6,
    start: dt.date = dt.date(2026, 4, 1),
) -> SyntheticStatement:
    rng = random.Random(seed)
    profile = _build_profile(rng, persona)
    holder = _person(rng)

    events: list[tuple[dt.date, Category, float]] = []
    for offset in range(months):
        index = start.month - 1 + offset
        events.extend(_month_events(rng, profile, start.year + index // 12, index % 12 + 1))
    events.sort(key=lambda e: (e[0], rng.random()))

    opening = float(round(profile.monthly_income * rng.uniform(0.5, 1.5)))
    balance = opening
    transactions: list[dict] = []

    for date, category, amount in events:
        is_debit = CATEGORY_INFO[category].txn_type == TxnType.DEBIT
        if is_debit and amount > balance:
            continue
        merchant, fragment = _counterparty(rng, profile, category, holder)
        channel = rng.choice(CHANNEL_CHOICES.get(category, [Channel.UPI]))
        balance = round(balance - amount if is_debit else balance + amount, 2)
        transactions.append({
            "id": len(transactions) + 1,
            "date": date.isoformat(),
            "narration": _narrate(rng, channel, fragment, is_debit),
            "amount": amount,
            "txn_type": CATEGORY_INFO[category].txn_type.value,
            "channel": channel.value,
            "merchant": merchant,
            "category": category.value,
            "balance": balance,
        })

    end_index = start.month - 1 + months - 1
    period_end = _date(start.year + end_index // 12, end_index % 12 + 1, 31)

    return SyntheticStatement(
        statement_id=f"stmt-{seed:05d}",
        persona=persona,
        holder=holder,
        bank=rng.choice(BANKS),
        period_start=start,
        period_end=period_end,
        opening_balance=opening,
        closing_balance=balance,
        transactions=transactions,
    )


if __name__ == "__main__":
    for seed, persona in [(1, "salaried"), (2, "gig"), (3, "business")]:
        stmt = generate_statement(seed, persona)
        assert stmt == generate_statement(seed, persona), "generator is not deterministic"

        credits = sum(t["amount"] for t in stmt.transactions if t["txn_type"] == "credit")
        debits = sum(t["amount"] for t in stmt.transactions if t["txn_type"] == "debit")
        assert abs(stmt.opening_balance + credits - debits - stmt.closing_balance) < 0.01
        assert all(t["balance"] >= 0 for t in stmt.transactions)

        print(f"{stmt.persona} | {stmt.holder} | {stmt.bank} | {stmt.period_start} to {stmt.period_end}")
        print(f"opening {stmt.opening_balance:,.2f} | closing {stmt.closing_balance:,.2f} | {len(stmt.transactions)} transactions")
        top = Counter(t["category"] for t in stmt.transactions).most_common(6)
        print("top categories:", ", ".join(f"{c}:{n}" for c, n in top))
        for t in stmt.transactions[:8]:
            print(f"{t['id']:>3} {t['date']} {t['txn_type'][0].upper()} {t['amount']:>10,.2f} {t['balance']:>12,.2f}  {t['category']:<16} {t['narration']}")
        print()

    print("all checks passed")