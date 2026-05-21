from dataclasses import dataclass


@dataclass
class ProposalSection:
    id: int
    title: str
    required: bool
    ai_generated: bool



@dataclass
class GBBResult:
    tier: str
    multiplier: float
    adjusted_price: float
    description: str
