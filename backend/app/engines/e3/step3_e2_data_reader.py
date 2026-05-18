from app.engines.e2.models import PricingSummary

_SI_DISCOUNT = 0.15  # must match step4_gap_analyzer._SI_DISCOUNT_RATE


def read_e2_data(summary: PricingSummary) -> dict:
    matched_items = []
    for m in summary.matched_items:
        qty = m.rfp_item.quantity if m.rfp_item.quantity is not None else 1.0
        matched_items.append({
            "sku": m.sku,
            "product_name": m.product_name,
            "qty": qty,
            "unit_price": m.unit_price,
            "line_total": round(qty * m.unit_price * (1 - _SI_DISCOUNT), 2),
        })

    unmatched_items = [
        {
            "description": m.rfp_item.description,
            "qty": m.rfp_item.quantity,
        }
        for m in summary.unmatched_items
    ]

    return {
        "matched_items": matched_items,
        "unmatched_items": unmatched_items,
        "subtotal": summary.subtotal,
        "discount_amount": summary.discount_amount,
        "total": summary.total,
        "currency": summary.currency,
    }
