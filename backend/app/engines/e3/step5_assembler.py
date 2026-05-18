from .models import GBBResult, ProposalSection

_PLACEHOLDER = "[Section content to be completed manually]"
_OPTIONAL_PREFIX = "OPTIONAL — REMOVE IF NOT NEEDED\n\n"

_COMMERCIAL_SECTION_TITLE = "Commercial Proposal"
_COMPLIANCE_SECTION_TITLE = "Compliance Matrix"


def _build_pricing_table(e2_data: dict, gbb_result: GBBResult) -> str:
    items = e2_data.get("matched_items", [])
    currency = e2_data.get("currency", "USD")

    lines = [
        "PRICING SUMMARY",
        f"GBB Tier: {gbb_result.tier.upper()} — {gbb_result.description}",
        "",
        f"{'SKU':<20} {'Description':<45} {'Qty':>5} {'Unit Price':>14} {'Line Total':>14}",
        "-" * 100,
    ]
    for item in items:
        lines.append(
            f"{item['sku']:<20} {item['product_name']:<45} "
            f"{item['qty']:>5} "
            f"{currency} {item['unit_price']:>11,.2f} "
            f"{currency} {item['line_total']:>9,.2f}"
        )

    unmatched = e2_data.get("unmatched_items", [])
    if unmatched:
        lines.append("")
        lines.append("ITEMS REQUIRING MANUAL SPECIFICATION:")
        for u in unmatched:
            qty_label = str(u["qty"]) if u["qty"] is not None else "TBD"
            lines.append(f"  - {u['description']} (qty: {qty_label})")

    lines += [
        "",
        "-" * 100,
        f"{'Subtotal':<72} {currency} {e2_data.get('subtotal', 0.0):>9,.2f}",
        f"{'Discount (15% SI)':<72} {currency} {e2_data.get('discount_amount', 0.0):>9,.2f}",
        f"{'TOTAL ({} tier)'.format(gbb_result.tier.upper()):<72} {currency} {gbb_result.adjusted_price:>9,.2f}",
    ]
    return "\n".join(lines)


def _build_compliance_summary(e1_data: dict) -> str:
    reqs = e1_data.get("requirements", [])
    if not reqs:
        return _PLACEHOLDER

    compliant = [r for r in reqs if (r.get("compliance_status") or "").lower() == "compliant"]
    non_compliant = [r for r in reqs if (r.get("compliance_status") or "").lower() == "non-compliant"]
    not_assessed = [r for r in reqs if r.get("compliance_status") is None
                    or r.get("compliance_status", "").lower() not in ("compliant", "non-compliant")]

    lines = [
        f"COMPLIANCE SUMMARY — {len(reqs)} requirements reviewed",
        f"  Compliant:      {len(compliant)}",
        f"  Non-compliant:  {len(non_compliant)}",
        f"  Not assessed:   {len(not_assessed)}",
        "",
    ]

    categories = {}
    for r in reqs:
        cat = (r.get("category") or "general").upper()
        categories.setdefault(cat, []).append(r)

    for cat, cat_reqs in sorted(categories.items()):
        lines.append(f"[{cat}]")
        for r in cat_reqs:
            status = r.get("compliance_status") or "Not assessed"
            lines.append(f"  [{status}] {r.get('text', '')}")
        lines.append("")

    traps = e1_data.get("legal_traps", [])
    if traps:
        lines.append("CONTRACTUAL RISK FLAGS:")
        for t in traps:
            lines.append(f"  - {t}")

    return "\n".join(lines)


def assemble_proposal(
    sections: list[ProposalSection],
    narratives: dict[int, str],
    e1_data: dict,
    e2_data: dict,
    gbb_result: GBBResult,
) -> list[dict]:
    pricing_table = _build_pricing_table(e2_data, gbb_result)
    compliance_summary = _build_compliance_summary(e1_data)

    assembled = []
    for section in sections:
        content = narratives.get(section.id, _PLACEHOLDER)

        if section.title == _COMMERCIAL_SECTION_TITLE:
            content = pricing_table
        elif section.title == _COMPLIANCE_SECTION_TITLE:
            content = compliance_summary

        if not section.required and content == _PLACEHOLDER:
            content = _OPTIONAL_PREFIX + content

        assembled.append({
            "id": section.id,
            "title": section.title,
            "content": content,
            "required": section.required,
            "ai_generated": section.ai_generated,
        })

    return assembled


if __name__ == "__main__":
    from app.engines.e3.step1_template_selector import select_template
    from app.engines.e3.step8_gbb_pricing import calculate_gbb

    sample_e1 = {
        "project_name": "Riyadh Campus Network",
        "requirements": [
            {"text": "48-port PoE+ switches", "category": "mandatory", "compliance_status": "Compliant"},
            {"text": "10G uplinks", "category": "mandatory", "compliance_status": "Compliant"},
            {"text": "3-year on-site support", "category": "optional", "compliance_status": None},
        ],
        "legal_traps": ["Liquidated damages: 0.5%/day uncapped"],
        "missing_documents": [],
    }
    sample_e2 = {
        "matched_items": [
            {"sku": "C9300-48P-E", "product_name": "Cisco Catalyst 9300 48-Port PoE+", "qty": 10,
             "unit_price": 7200.0, "line_total": 61200.0},
        ],
        "unmatched_items": [{"description": "Legacy serial console server", "qty": 1}],
        "subtotal": 61200.0, "discount_amount": 9180.0, "total": 52020.0, "currency": "USD",
    }
    gbb = calculate_gbb(52020.0, "better")
    sections = select_template("rfp")
    narratives = {s.id: "[Section content to be completed manually]" for s in sections}

    result = assemble_proposal(sections, narratives, sample_e1, sample_e2, gbb)
    for s in result:
        print(f"\n[{s['id']}] {s['title']} (required={s['required']}, ai={s['ai_generated']})")
        print(s["content"][:200])
