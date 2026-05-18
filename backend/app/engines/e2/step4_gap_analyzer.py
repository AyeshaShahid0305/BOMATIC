from .models import CatalogMatch, PricingSummary

_SI_DISCOUNT_RATE = 0.15
_LOW_CONFIDENCE_CEILING = 0.50


def analyze_gaps(matches: list[CatalogMatch]) -> PricingSummary:
    matched: list[CatalogMatch] = []
    unmatched: list[CatalogMatch] = []
    low_confidence: list[CatalogMatch] = []

    for m in matches:
        if m.match_method == "unmatched":
            unmatched.append(m)
        elif m.match_score < _LOW_CONFIDENCE_CEILING:
            low_confidence.append(m)
        else:
            matched.append(m)

    subtotal = 0.0
    for m in matched:
        qty = m.rfp_item.quantity if m.rfp_item.quantity is not None else 1.0
        subtotal += qty * m.unit_price

    discount_amount = round(subtotal * _SI_DISCOUNT_RATE, 2)
    subtotal = round(subtotal, 2)
    total = round(subtotal - discount_amount, 2)

    return PricingSummary(
        matched_items=matched,
        unmatched_items=unmatched,
        low_confidence_items=low_confidence,
        subtotal=subtotal,
        discount_amount=discount_amount,
        total=total,
    )


if __name__ == "__main__":
    from app.engines.e2.models import RFPLineItem

    samples = [
        CatalogMatch(
            rfp_item=RFPLineItem(description="Cisco ASA 5516-X firewall", quantity=2, unit="units", category="security", raw_text="", confidence=0.9),
            sku="ASA5516-FPWR-K9", product_name="Cisco ASA 5516-X with FirePOWER Services",
            vendor="Cisco", unit_price=4995.00, match_score=1.0, match_method="exact",
        ),
        CatalogMatch(
            rfp_item=RFPLineItem(description="48-port PoE+ switch", quantity=10, unit="units", category="network", raw_text="", confidence=0.85),
            sku="C9300-48P-E", product_name="Cisco Catalyst 9300 48-Port PoE+ Switch",
            vendor="Cisco", unit_price=7200.00, match_score=0.42, match_method="fuzzy",
        ),
        CatalogMatch(
            rfp_item=RFPLineItem(description="DNA license subscription", quantity=10, unit="licenses", category="license", raw_text="", confidence=0.8),
            sku="C9300-DNA-A-3Y", product_name="Cisco DNA Advantage License",
            vendor="Cisco", unit_price=450.00, match_score=0.35, match_method="fuzzy",
        ),
        CatalogMatch(
            rfp_item=RFPLineItem(description="unmanaged desktop hub", quantity=1, unit="units", category="hardware", raw_text="", confidence=0.6),
            sku="", product_name="", vendor="", unit_price=0.0, match_score=0.0, match_method="unmatched",
        ),
    ]

    summary = analyze_gaps(samples)
    print(f"Matched:         {len(summary.matched_items)}")
    print(f"Low-confidence:  {len(summary.low_confidence_items)}")
    print(f"Unmatched:       {len(summary.unmatched_items)}")
    print(f"Subtotal:        {summary.currency} {summary.subtotal:,.2f}")
    print(f"Discount (15%):  {summary.currency} {summary.discount_amount:,.2f}")
    print(f"Total:           {summary.currency} {summary.total:,.2f}")
