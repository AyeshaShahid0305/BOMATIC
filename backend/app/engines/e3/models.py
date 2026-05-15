from dataclasses import dataclass


@dataclass
class ProposalSection:
    id: int
    title: str
    required: bool
    ai_generated: bool


@dataclass
class ProposalConfig:
    project_type: str
    sections: list
    gbb_tier: str
    gbb_multiplier: float


@dataclass
class GBBResult:
    tier: str
    multiplier: float
    adjusted_price: float
    description: str
