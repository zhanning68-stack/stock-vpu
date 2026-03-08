import re
from dataclasses import dataclass, field
from typing import Optional

STOCK_CODE_PATTERN = re.compile(
    r"^(sh|sz)?"
    r"(6\d{5}"  # 主板 600/601/603
    r"|000\d{3}"  # 主板 000
    r"|001\d{3}"  # 主板 001
    r"|002\d{3}"  # 中小板 002
    r"|003\d{3}"  # 主板 003
    r"|300\d{3}"  # 创业板 300
    r"|301\d{3}"  # 创业板 301
    r"|688\d{3}"  # 科创板 688
    r")$"
)


def validate_stock_code(code: str) -> bool:
    """验证股票代码格式是否合法"""
    return bool(STOCK_CODE_PATTERN.match(code.strip().lower()))


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
