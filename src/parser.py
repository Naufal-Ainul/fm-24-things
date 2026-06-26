import json
import re
from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup


# ============================================================
# HTML LOADER
# ============================================================

def load_html(path: Path) -> BeautifulSoup:
    """
    Membaca file HTML FM24.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


# ============================================================
# TABLE EXTRACTOR
# ============================================================

def extract_table(soup: BeautifulSoup):
    """
    Mengubah tabel HTML menjadi list of dictionary.
    """

    table = soup.find("table")

    if table is None:
        raise ValueError("Table tidak ditemukan.")

    headers = [
        th.get_text(strip=True)
        for th in table.find_all("th")
    ]

    rows = []

    for tr in table.find_all("tr")[1:]:

        cols = [
            td.get_text(strip=True)
            for td in tr.find_all("td")
        ]

        if len(cols) != len(headers):
            continue

        rows.append(dict(zip(headers, cols)))

    return rows


# ============================================================
# DATA CONVERTER
# ============================================================

def to_int(value):

    if value in ("", "-", None):
        return None

    try:
        return int(value)

    except:
        return None


def to_float(value):

    if value in ("", "-", None):
        return None

    try:
        return float(value)

    except:
        return None


def parse_salary(value):

    """
    "$29,234,000 p/a"

    →

    29234000
    """

    if value in ("", "-", None):
        return None

    value = re.sub(r"[^\d]", "", value)

    if value == "":
        return None

    return int(value)


def parse_date(value):

    """
    6/30/2030

    →

    2030-06-30
    """

    if value in ("", "-", None):
        return None

    try:

        return datetime.strptime(
            value,
            "%m/%d/%Y"
        ).strftime("%Y-%m-%d")

    except:

        return value


# ============================================================
# NORMALIZER (SQUAD)
# ============================================================

def normalize_player(player):

    salary = parse_salary(
        player.get("Salary")
    )

    ca = to_int(
        player.get("CA")
    )

    pa = to_int(
        player.get("PA")
    )

    position = player.get(
        "Position",
        ""
    )

    positions = [
        p.strip()
        for p in position.split(",")
        if p.strip()
    ]

    return {

        "name":
            player.get("Name"),

        "age":
            to_int(
                player.get("Age")
            ),

        "position":
            position,

        "primary_position":
            positions[0] if positions else None,

        "secondary_positions":
            positions[1:] if len(positions) > 1 else [],

        "ca":
            ca,

        "pa":
            pa,

        "potential_gap":
            (
                pa - ca
            )
            if ca is not None
            and pa is not None
            else None,

        "contract_expiry":
            parse_date(
                player.get("Expires")
            ),

        "salary":
            salary,

        "salary_million":
            round(
                salary / 1_000_000,
                2
            )
            if salary
            else None,

        "personality":
            player.get("Personality"),

        "determination":
            to_int(
                player.get("Det")
            ),

        "average_rating":
            to_float(
                player.get("Av Rat")
            )
    }


# ============================================================
# CLEAN DATASET
# ============================================================

def clean_dataset(players):

    return [
        normalize_player(player)
        for player in players
    ]


# ============================================================
# PARSER
# ============================================================

def parse_squad(path: Path):

    soup = load_html(path)

    raw = extract_table(soup)

    return clean_dataset(raw)


def parse_tactical(path: Path):

    soup = load_html(path)

    return extract_table(soup)


# ============================================================
# JSON EXPORT
# ============================================================

def export_json(data, output_path: Path):

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"[✓] JSON berhasil disimpan -> {output_path}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    BASE_DIR = Path(__file__).resolve().parent.parent

    squad_html = (
        BASE_DIR
        / "dataset"
        / "squad-audit_06-26-002.html"
    )

    tactical_html = (
        BASE_DIR
        / "dataset"
        / "tactical-audit-06-26.html"
    )

    output_dir = (
        BASE_DIR
        / "output"
        / "raw"
    )

    # Parse
    squad_data = parse_squad(squad_html)

    tactical_data = parse_tactical(tactical_html)

    # Export
    export_json(
        squad_data,
        output_dir / "squad.json"
    )

    export_json(
        tactical_data,
        output_dir / "tactical.json"
    )

    print("\n===== SAMPLE PLAYER =====\n")

    print(json.dumps(
        squad_data[0],
        indent=4,
        ensure_ascii=False
    ))
