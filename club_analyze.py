import pandas as pd

# ==========================
# KONFIGURASI
# ==========================

FACILITY_MAP = {
    "poor": 10,
    "basic": 20,
    "adequate": 40,
    "average": 50,
    "good": 60,
    "great": 70,
    "superb": 80,
    "excellent": 90,
    "exceptional": 95,
    "state of the art": 100
}

# ==========================
# FUNGSI BANTUAN
# ==========================

def get_facility_score(prompt):
    while True:
        value = input(prompt).strip().lower()

        if value in FACILITY_MAP:
            return FACILITY_MAP[value]

        print("\nNilai tidak valid!")
        print("Pilihan:")
        print(", ".join(FACILITY_MAP.keys()))
        print()


def normalize_balance(balance):
    MAX_BALANCE = 500_000_000
    return min((balance / MAX_BALANCE) * 100, 100)


def normalize_debt(debt):
    MAX_DEBT = 1_000_000_000
    score = 100 - min((debt / MAX_DEBT) * 100, 100)
    return max(score, 0)


def normalize_transfer_budget(budget):
    MAX_TRANSFER = 200_000_000
    return min((budget / MAX_TRANSFER) * 100, 100)


def normalize_wage_budget(wage):
    MAX_WAGE = 7_000_000
    return min((wage / MAX_WAGE) * 100, 100)


def normalize_reputation(rep):
    """
    Input 0-100
    """
    return max(0, min(rep, 100))


def normalize_squad_age(age):
    """
    Ideal 20-24 tahun
    """

    if 20 <= age <= 24:
        return 100

    diff = abs(age - 22)

    score = max(0, 100 - (diff * 8))

    return score


def calculate_finance_score(
    balance,
    debt,
    transfer_budget,
    wage_budget
):
    balance_score = normalize_balance(balance)
    debt_score = normalize_debt(debt)
    transfer_score = normalize_transfer_budget(
        transfer_budget
    )
    wage_score = normalize_wage_budget(
        wage_budget
    )

    finance_score = (
        balance_score * 0.4 +
        debt_score * 0.3 +
        transfer_score * 0.2 +
        wage_score * 0.1
    )

    return round(finance_score, 2)


def calculate_long_term_score(
    youth_facilities,
    youth_recruitment,
    finance_score,
    training_facilities,
    reputation,
    squad_age_score
):

    score = (
        youth_facilities * 0.25 +
        youth_recruitment * 0.20 +
        finance_score * 0.25 +
        training_facilities * 0.15 +
        reputation * 0.10 +
        squad_age_score * 0.05
    )

    return round(score, 2)


# ==========================
# MAIN PROGRAM
# ==========================

clubs = []

print("=" * 50)
print("FOOTBALL MANAGER LONG-TERM CLUB ANALYZER")
print("=" * 50)

while True:

    print("\nMasukkan Data Klub")
    print("-" * 30)

    club_name = input("Nama Klub: ")

    youth_facilities = get_facility_score(
        "Youth Facilities: "
    )

    training_facilities = get_facility_score(
        "Training Facilities: "
    )

    youth_recruitment = get_facility_score(
        "Youth Recruitment: "
    )

    reputation = float(
        input(
            "Reputation (0-100): "
        )
    )

    balance = float(
        input(
            "Balance (€): "
        )
    )

    debt = float(
        input(
            "Debt (€): "
        )
    )

    transfer_budget = float(
        input(
            "Transfer Budget (€): "
        )
    )

    wage_budget = float(
        input(
            "Wage Budget (€ per week): "
        )
    )

    squad_age = float(
        input(
            "Average Squad Age: "
        )
    )

    finance_score = calculate_finance_score(
        balance,
        debt,
        transfer_budget,
        wage_budget
    )

    squad_age_score = normalize_squad_age(
        squad_age
    )

    total_score = calculate_long_term_score(
        youth_facilities,
        youth_recruitment,
        finance_score,
        training_facilities,
        reputation,
        squad_age_score
    )

    clubs.append({
        "Club": club_name,
        "Youth Facilities": youth_facilities,
        "Youth Recruitment": youth_recruitment,
        "Training Facilities": training_facilities,
        "Reputation": reputation,
        "Balance": balance,
        "Debt": debt,
        "Transfer Budget": transfer_budget,
        "Wage Budget": wage_budget,
        "Squad Age": squad_age,
        "Finance Score": finance_score,
        "Total Score": total_score
    })

    again = input(
        "\nTambah klub lagi? (y/n): "
    ).lower()

    if again != "y":
        break

# ==========================
# HASIL
# ==========================

df = pd.DataFrame(clubs)

df = df.sort_values(
    by="Total Score",
    ascending=False
)

df.insert(
    0,
    "Rank",
    range(1, len(df) + 1)
)

print("\n")
print("=" * 60)
print("RANKING KLUB")
print("=" * 60)

print(
    df[
        [
            "Rank",
            "Club",
            "Finance Score",
            "Total Score"
        ]
    ].to_string(index=False)
)

# ==========================
# EXPORT EXCEL
# ==========================

export = input(
    "\nExport ke Excel? (y/n): "
).lower()

if export == "y":

    filename = "fm_long_term_club_analysis.xlsx"

    df.to_excel(
        filename,
        index=False
    )

    print(
        f"\nFile berhasil disimpan: {filename}"
    )

else:
    print(
        "\nProgram selesai."
    )