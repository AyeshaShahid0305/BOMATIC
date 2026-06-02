"""
Cost Stack - CS-001 through CS-009.

All arithmetic uses decimal.Decimal to avoid floating-point rounding errors.
All public functions take and return plain Python floats for interop.
"""

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .models import PricingSummary

_DATA_DIR = Path(__file__).parent / "data"
_FX_PATH = _DATA_DIR / "fx_rates.json"
_VAT_PATH = _DATA_DIR / "vat_rates.json"
_DEFAULTS_PATH = _DATA_DIR / "cost_stack_defaults.json"


def load_defaults() -> dict:
    with open(_DEFAULTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_fx_rates() -> dict[str, float]:
    with open(_FX_PATH, encoding="utf-8") as f:
        return json.load(f)["rates"]


def _load_vat_rates() -> dict[str, dict]:
    with open(_VAT_PATH, encoding="utf-8") as f:
        return json.load(f)["rates"]


def _d(v: float | int | str) -> Decimal:
    """Convert to Decimal for safe arithmetic."""
    return Decimal(str(v))


def _round2(v: Decimal) -> float:
    """Round to 2 decimal places and return as float."""
    return float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def cs001_currency_convert(
    amount_usd: float,
    target_currency: str,
    fx_rates: dict[str, float],
) -> tuple[float, float]:
    """Convert amount from USD to target_currency."""
    rate = _d(fx_rates.get(target_currency, 1.0))
    converted = _d(amount_usd) * rate
    return _round2(converted), float(rate)


def cs002_vendor_discount(list_price_local: float, discount_pct: float) -> float:
    """Apply vendor trade discount."""
    result = _d(list_price_local) * (Decimal("1") - _d(discount_pct))
    return _round2(result)


def cs003_inhouse_margin(cost: float, margin_pct: float) -> float:
    """Add inhouse SI margin to cost."""
    result = _d(cost) * (Decimal("1") + _d(margin_pct))
    return _round2(result)


def cs004_overhead(cost: float, components: dict[str, float]) -> float:
    """Calculate overhead amount."""
    total_pct = sum((_d(v) for v in components.values()), Decimal("0"))
    result = _d(cost) * total_pct
    return _round2(result)


def cs005_cost_with_overhead(cost: float, overhead: float) -> float:
    """Total cost including overhead."""
    return _round2(_d(cost) + _d(overhead))


def cs006_selling_price(cost_with_overhead: float, mode: str, pct: float) -> float:
    """
    Calculate selling price.
    mode='margin': sell = cost / (1 - pct)
    mode='markup': sell = cost * (1 + pct)
    """
    if mode == "markup":
        result = _d(cost_with_overhead) * (Decimal("1") + _d(pct))
    else:
        if _d(pct) >= Decimal("1"):
            raise ValueError("Margin pct must be < 1.0 (< 100%)")
        result = _d(cost_with_overhead) / (Decimal("1") - _d(pct))
    return _round2(result)


def cs007_extended_sell(
    selling_price: float,
    embed_discounts: list[dict[str, Any]],
) -> float:
    """Apply embed/project discounts sequentially."""
    result = _d(selling_price)
    for discount in embed_discounts:
        pct = _d(discount.get("pct", 0))
        result = result * (Decimal("1") - pct)
    return _round2(result)


def cs008_stcs_sale(extended_sell: float, revenue_share_pct: float) -> float:
    """STCS/distributor revenue share deduction."""
    result = _d(extended_sell) * (Decimal("1") - _d(revenue_share_pct))
    return _round2(result)


def cs009_vat(amount: float, country_code: str, vat_rates: dict[str, dict]) -> tuple[float, float]:
    """Calculate VAT and return (vat_amount, vat_rate_used)."""
    rate = _d(vat_rates.get(country_code, {}).get("rate", 0.0))
    vat_amount = _d(amount) * rate
    return _round2(vat_amount), float(rate)


def run_cost_stack(summary: PricingSummary, config: dict) -> dict:
    """Apply CS-001 - CS-009 to all matched items in summary."""
    fx_rates = _load_fx_rates()
    vat_rates_data = _load_vat_rates()

    target_currency = config.get("target_currency", "SAR")
    vendor_discount_pct = config.get("vendor_discount_pct", 0.30)
    inhouse_margin_pct = config.get("inhouse_margin_pct", 0.10)
    overhead_components = config.get("overhead_components", {})
    selling_mode = config.get("selling_mode", "margin")
    selling_pct = config.get("selling_pct", 0.25)
    embed_discounts = config.get("embed_discounts", [])
    revenue_share_pct = config.get("revenue_share_pct", 0.05)
    vat_country = config.get("vat_country", "SA")

    line_items = []
    total_list_local = Decimal("0")
    total_cost = Decimal("0")
    total_overhead_sum = Decimal("0")
    total_sell = Decimal("0")
    total_extended = Decimal("0")
    total_vat = Decimal("0")

    for m in summary.matched_items:
        qty = m.rfp_item.quantity if m.rfp_item.quantity is not None else 1.0
        qty_dec = _d(qty)
        line_list_usd = _round2(_d(m.unit_price) * qty_dec)

        list_local, fx_rate = cs001_currency_convert(line_list_usd, target_currency, fx_rates)
        unit_local = _round2(_d(list_local) / qty_dec)
        after_discount = cs002_vendor_discount(list_local, vendor_discount_pct)
        after_inhouse = cs003_inhouse_margin(after_discount, inhouse_margin_pct)
        overhead_amt = cs004_overhead(after_inhouse, overhead_components)
        cost_total = cs005_cost_with_overhead(after_inhouse, overhead_amt)
        sell_price = cs006_selling_price(cost_total, selling_mode, selling_pct)
        extended = cs007_extended_sell(sell_price, embed_discounts)
        stcs = cs008_stcs_sale(extended, revenue_share_pct)
        vat_amt, vat_rate = cs009_vat(extended, vat_country, vat_rates_data)
        total_with_vat = _round2(_d(extended) + _d(vat_amt))

        line_items.append({
            "sku": m.sku,
            "description": m.rfp_item.description,
            "qty": qty,
            "unit_list_usd": m.unit_price,
            "line_list_usd": line_list_usd,
            "fx_rate": fx_rate,
            "unit_list_local": unit_local,
            "cs001_line_list_local": list_local,
            "cs002_after_vendor_discount": after_discount,
            "cs003_after_inhouse_margin": after_inhouse,
            "cs004_overhead": overhead_amt,
            "cs005_cost_with_overhead": cost_total,
            "cs006_selling_price": sell_price,
            "cs007_extended_sell": extended,
            "cs008_stcs_sale": stcs,
            "cs009_vat": vat_amt,
            "vat_rate": vat_rate,
            "line_total_with_vat": total_with_vat,
            "currency": target_currency,
        })

        total_list_local += _d(list_local)
        total_cost += _d(cost_total)
        total_overhead_sum += _d(overhead_amt)
        total_sell += _d(extended)
        total_extended += _d(extended)
        total_vat += _d(vat_amt)

    stcs_total = cs008_stcs_sale(_round2(total_extended), revenue_share_pct)
    _, vat_rate_used = cs009_vat(1.0, vat_country, vat_rates_data)

    return {
        "line_items": line_items,
        "summary": {
            "total_list_local": _round2(total_list_local),
            "total_cost": _round2(total_cost),
            "total_overhead": _round2(total_overhead_sum),
            "total_sell": _round2(total_sell),
            "cs008_stcs_sale_total": stcs_total,
            "total_vat": _round2(total_vat),
            "total_with_vat": _round2(total_sell + total_vat),
            "currency": target_currency,
            "fx_rate": fx_rates.get(target_currency, 1.0),
            "vat_rate": vat_rate_used,
            "vat_country": vat_country,
            "line_count": len(line_items),
        },
        "config_used": config,
    }
