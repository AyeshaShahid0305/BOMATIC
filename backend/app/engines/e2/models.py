from dataclasses import dataclass


@dataclass
class BoQDetectionResult:
    format_type: str
    confidence: float
    sheet_name: str
    header_row_index: int


@dataclass
class BoQLineItem:
    part_number: str
    description: str
    qty: int
    unit_price_usd: float
    total_price_usd: float
    line_type: str
