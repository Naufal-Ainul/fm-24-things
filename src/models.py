# core/models.py

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Player:

    # ======================================================
    # BASIC INFORMATION
    # ======================================================

    name: str
    age: int

    position: str
    primary_position: str
    secondary_positions: list[str] = field(default_factory=list)

    # ======================================================
    # ABILITY
    # ======================================================

    ca: int = 0
    pa: int = 0

    # ======================================================
    # CONTRACT
    # ======================================================

    contract_expiry: Optional[str] = None

    salary: Optional[int] = None

    # ======================================================
    # PERSONALITY
    # ======================================================

    personality: str = ""

    determination: int = 0

    # ======================================================
    # PERFORMANCE
    # ======================================================

    average_rating: Optional[float] = None

    # ======================================================
    # ATTRIBUTES
    #
    # Semua atribut FM24 disimpan di sini
    #
    # contoh:
    #
    # Passing
    # Vision
    # Pace
    # Technique
    # First Touch
    # Tackling
    #
    # dst...
    # ======================================================

    attributes: dict[str, int] = field(
        default_factory=dict
    )

    # ======================================================
    # ANALYSIS SCORE
    # ======================================================

    ability_score: float = 0.0

    potential_score: float = 0.0

    personality_score: float = 0.0

    contract_score: float = 0.0

    tactical_score: float = 0.0

    financial_score: float = 0.0

    development_index: float = 0.0

    recommendation_score: float = 0.0

    # ======================================================
    # REASONING ENGINE
    # ======================================================

    recommendation: str = ""

    confidence: float = 0.0

    reasons: list[str] = field(
        default_factory=list
    )

    # ======================================================
    # HELPER PROPERTY
    # ======================================================

    @property
    def potential_gap(self) -> int:
        """
        PA - CA
        """

        return self.pa - self.ca

    @property
    def salary_million(self) -> Optional[float]:

        if self.salary is None:
            return None

        return round(
            self.salary / 1_000_000,
            2
        )

    @property
    def age_group(self) -> str:

        if self.age <= 18:
            return "Youth"

        elif self.age <= 21:
            return "Wonderkid"

        elif self.age <= 27:
            return "Prime"

        elif self.age <= 32:
            return "Experienced"

        else:
            return "Veteran"

    @property
    def has_high_potential(self) -> bool:

        return self.potential_gap >= 15

    @property
    def is_young(self) -> bool:

        return self.age <= 21

    @property
    def is_prime(self) -> bool:

        return 22 <= self.age <= 29

    @property
    def is_veteran(self) -> bool:

        return self.age >= 30

    # ======================================================
    # ATTRIBUTE HELPER
    # ======================================================

    def get_attribute(
        self,
        attribute_name: str,
        default: int = 0
    ) -> int:

        return self.attributes.get(
            attribute_name,
            default
        )

    def set_attribute(
        self,
        attribute_name: str,
        value: int
    ) -> None:

        self.attributes[
            attribute_name
        ] = value

    # ======================================================
    # STRING
    # ======================================================

    def __str__(self):

        return (
            f"{self.name}"
            f" | {self.primary_position}"
            f" | Age {self.age}"
            f" | CA {self.ca}"
            f" | PA {self.pa}"
        )
