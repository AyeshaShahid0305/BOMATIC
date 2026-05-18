from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RFPLineItem:
    description: str
    quantity: Optional[float]
    unit: str
    category: str
    raw_text: str
    confidence: float


@dataclass
class CatalogMatch:
    rfp_item: "RFPLineItem"
    sku: str
    product_name: str
    vendor: str
    unit_price: float
    match_score: float
    match_method: str  # "exact", "fuzzy", "unmatched"


@dataclass
class PricingSummary:
    matched_items: List["CatalogMatch"] = field(default_factory=list)
    unmatched_items: List["CatalogMatch"] = field(default_factory=list)
    low_confidence_items: List["CatalogMatch"] = field(default_factory=list)
    subtotal: float = 0.0
    discount_amount: float = 0.0
    total: float = 0.0
    currency: str = "USD"


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
