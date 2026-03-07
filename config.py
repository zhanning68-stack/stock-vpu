from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    PRICE_UNIT: float = 0.05
    TRIM_RATIO: float = 0.25
    MIN_VALID_UNITS: int = 10
    MIN_PRICE_SPREAD: float = 0.03
    MA_PERIODS: list = field(default_factory=lambda: [5, 10])
    SKIP_FIRST_LAST: bool = True
    ENABLE_DIRECTION: bool = True


config = Config()
