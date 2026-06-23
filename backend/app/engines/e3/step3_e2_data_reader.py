from app.schemas.pipeline import E2PricingArtifact

_SI_DISCOUNT = 0.15  # must match step4_gap_analyzer._SI_DISCOUNT_RATE


def read_e2_data(artifact: E2PricingArtifact) -> dict:
    matched_items = [
        {
            "sku": item.sku,
            "product_name": item.product_name,
            "qty": item.quantity if item.quantity is not None else 1.0,
            "unit_price": item.unit_price,
            "line_total": round(
                (item.quantity if item.quantity is not None else 1.0)
                * item.unit_price
                * (1 - _SI_DISCOUNT),
                2,
            ),
        }
        for item in artifact.matched_items
    ]
    unmatched_items = [
        {
            "description": item.description,
            "qty": item.quantity,
        }
        for item in artifact.unmatched_items
    ]

    return {
        "matched_items": matched_items,
        "unmatched_items": unmatched_items,
        "subtotal": artifact.subtotal,
        "discount_amount": artifact.discount_amount,
        "total": artifact.total,
        "currency": artifact.currency,
    }
