from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class E1Output(BaseModel):
    vendor_list: list[str]
    requirements_baseline: list[dict]
    risk_flags: list[dict]
    sector: str
    frameworks_selected: list[str]


class E2PricingLine(BaseModel):
    sku: str = ""
    product_name: str = ""
    description: str = ""
    quantity: float | None = None
    unit_price: float = Field(default=0.0, ge=0.0)


class E2PricingArtifact(BaseModel):
    """Versioned contract persisted by E2 and consumed by downstream engines."""

    model_config = ConfigDict(extra="ignore")

    artifact_type: Literal["e2_pricing"] = "e2_pricing"
    schema_version: Literal[1] = 1
    matched_items: list[E2PricingLine] = Field(default_factory=list)
    unmatched_items: list[E2PricingLine] = Field(default_factory=list)
    subtotal: float = Field(default=0.0, ge=0.0)
    discount_amount: float = Field(default=0.0, ge=0.0)
    total: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @classmethod
    def from_pricing_summary(cls, summary) -> "E2PricingArtifact":
        return cls(
            matched_items=[
                E2PricingLine(
                    sku=match.sku,
                    product_name=match.product_name,
                    description=match.rfp_item.description,
                    quantity=match.rfp_item.quantity,
                    unit_price=match.unit_price,
                )
                for match in summary.matched_items
            ],
            unmatched_items=[
                E2PricingLine(
                    description=match.rfp_item.description,
                    quantity=match.rfp_item.quantity,
                )
                for match in summary.unmatched_items
            ],
            subtotal=summary.subtotal,
            discount_amount=summary.discount_amount,
            total=summary.total,
            currency=summary.currency,
        )


class E4BaselineRequirement(BaseModel):
    question_id: str
    category: str = "General"
    question: str
    answer: str = ""
    priority: str = "must_have"
    expected_answer_type: str = "text"
    status: Literal["answered", "missing", "insufficient"]
    gap_reason: str | None = None


class E4BaselineArtifact(BaseModel):
    """Validated RFI response baseline persisted by E4 for downstream engines."""

    model_config = ConfigDict(extra="ignore")

    artifact_type: Literal["e4_requirements_baseline"] = "e4_requirements_baseline"
    schema_version: Literal[1] = 1
    source_filename: str
    requirements: list[E4BaselineRequirement] = Field(default_factory=list)
    answered_count: int = Field(default=0, ge=0)
    gap_count: int = Field(default=0, ge=0)
