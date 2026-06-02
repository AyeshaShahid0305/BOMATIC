# Codex Task: E2 Cost Stack CS-001 → CS-009

## Context

BOMATIC's E2 engine currently applies a flat 15% SI discount — that's it. The
architecture specifies a 9-step cost stack (CS-001 through CS-009) that handles
currency conversion, vendor discount, inhouse margin, overhead, selling price,
embed discounts, STCS revenue share, and VAT. The FX and VAT rate files created
in the previous task are the data foundation for this.

This task implements the full cost stack as pure Python functions and wires them
into the E2 pipeline. The Excel BoM workbook is extended to show all cost stack
columns. No frontend changes are needed — engineers see the cost stack via the
Excel download.

**Cost stack steps:**
- CS-001: Convert list price from USD to target currency using fx_rates.json
- CS-002: Apply vendor trade discount (% off list price)
- CS-003: Apply inhouse margin (SI cost uplift, adds to cost)
- CS-004: Calculate overhead (sum of 7 overhead component percentages × cost)
- CS-005: Cost with overhead = CS-003 result + CS-004 result
- CS-006: Selling price — either margin mode (cost / (1 - pct)) or markup mode (cost × (1 + pct))
- CS-007: Extended sell — apply embed discounts (e.g. volume, project discounts)
- CS-008: STCS sale — if selling through STCS/distributor, deduct revenue share
- CS-009: VAT — apply VAT rate for target country

**Default config** (in `cost_stack_defaults.json`):
- target_currency: SAR
- vendor_discount_pct: 0.30 (30% off list)
- inhouse_margin_pct: 0.10 (10% SI cost add)
- overhead_components: freight 2%, customs 5%, insurance 0.5%, warehousing 1%, handling 0.5%, finance 0.5%, contingency 0.5% = 10% total
- selling_mode: "margin"
- selling_pct: 0.25 (25% gross margin)
- embed_discounts: [] (none by default)
- revenue_share_pct: 0.05 (5% STCS share)
- vat_country: SA

**Important:** use `decimal.Decimal` for all arithmetic to avoid floating-point
rounding errors. Never use plain `float` math for money calculations.

---

## Step 1 — Read these files first

1. `backend/app/engines/e2/step4_gap_analyzer.py`
2. `backend/app/engines/e2/step5_excel_writer.py`
3. `backend/app/engines/e2/pipeline.py`
4. `backend/app/engines/e2/models.py`
5. `backend/app/engines/e2/data/fx_rates.json`
6. `backend/app/engines/e2/data/vat_rates.json`
7. `backend/app/api/e2_routes.py`

---

## Step 2 — Create `backend/app/engines/e2/data/cost_stack_defaults.json`

```json
{
  "target_currency": "SAR",
  "vendor_discount_pct": 0.30,
  "inhouse_margin_pct": 0.10,
  "overhead_components": {
    "freight": 0.02,
    "customs": 0.05,
    "insurance": 0.005,
    "warehousing": 0.01,
    "handling": 0.005,
    "finance": 0.005,
    "contingency": 0.005
  },
  "selling_mode": "margin",
  "selling_pct": 0.25,
  "embed_discounts": [],
  "revenue_share_pct": 0.05,
  "vat_country": "SA"
}
```

---

## Step 3 — Create `backend/app/engines/e2/step6_cost_stack.py`

```python
"""
Cost Stack — CS-001 through CS-009.

All arithmetic uses decimal.Decimal to avoid floating-point rounding errors.
All public functions take and return plain Python floats for interop.

Usage:
    from app.engines.e2.step6_cost_stack import run_cost_stack, load_defaults

    config = load_defaults()          # or override fields
    result = run_cost_stack(summary, config)
    # result["line_items"] — per-line cost breakdown
    # result["summary"]    — totals across all lines
"""

import json
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .models import PricingSummary

_DATA_DIR = Path(__file__).parent / "data"
_FX_PATH = _DATA_DIR / "fx_rates.json"
_VAT_PATH = _DATA_DIR / "vat_rates.json"
_DEFAULTS_PATH = _DATA_DIR / "cost_stack_defaults.json"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_defaults() -> dict:
    with open(_DEFAULTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_fx_rates() -> dict[str, float]:
    with open(_FX_PATH, encoding="utf-8") as f:
        return json.load(f)["rates"]


def _load_vat_rates() -> dict[str, dict]:
    with open(_VAT_PATH, encoding="utf-8") as f:
        return json.load(f)["rates"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _d(v: float | int | str) -> Decimal:
    """Convert to Decimal for safe arithmetic."""
    return Decimal(str(v))


def _round2(v: Decimal) -> float:
    """Round to 2 decimal places and return as float."""
    return float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# CS-001 through CS-009 — pure functions
# ---------------------------------------------------------------------------

def cs001_currency_convert(amount_usd: float, target_currency: str,
                            fx_rates: dict[str, float]) -> tuple[float, float]:
    """
    Convert amount from USD to target_currency.
    Returns (converted_amount, fx_rate_used).
    """
    rate = _d(fx_rates.get(target_currency, 1.0))
    converted = _d(amount_usd) * rate
    return _round2(converted), float(rate)


def cs002_vendor_discount(list_price_local: float, discount_pct: float) -> float:
    """
    Apply vendor trade discount.
    cost_after_discount = list_price × (1 - discount_pct)
    """
    result = _d(list_price_local) * (1 - _d(discount_pct))
    return _round2(result)


def cs003_inhouse_margin(cost: float, margin_pct: float) -> float:
    """
    Add inhouse SI margin to cost.
    cost_with_margin = cost × (1 + margin_pct)
    """
    result = _d(cost) * (1 + _d(margin_pct))
    return _round2(result)


def cs004_overhead(cost: float, components: dict[str, float]) -> float:
    """
    Calculate overhead amount.
    overhead = cost × sum(component_percentages)
    """
    total_pct = sum(_d(v) for v in components.values())
    result = _d(cost) * total_pct
    return _round2(result)


def cs005_cost_with_overhead(cost: float, overhead: float) -> float:
    """Total cost including overhead."""
    return _round2(_d(cost) + _d(overhead))


def cs006_selling_price(cost_with_overhead: float, mode: str, pct: float) -> float:
    """
    Calculate selling price.
    mode='margin': sell = cost / (1 - pct)   [gross margin target]
    mode='markup': sell = cost × (1 + pct)   [markup on cost]
    """
    if mode == "markup":
        result = _d(cost_with_overhead) * (1 + _d(pct))
    else:  # margin
        if _d(pct) >= Decimal("1"):
            raise ValueError("Margin pct must be < 1.0 (< 100%)")
        result = _d(cost_with_overhead) / (1 - _d(pct))
    return _round2(result)


def cs007_extended_sell(selling_price: float,
                         embed_discounts: list[dict[str, Any]]) -> float:
    """
    Apply embed/project discounts sequentially.
    Each discount: {"name": str, "pct": float}
    extended_sell = selling_price × ∏(1 - pct_i)
    """
    result = _d(selling_price)
    for discount in embed_discounts:
        pct = _d(discount.get("pct", 0))
        result = result * (1 - pct)
    return _round2(result)


def cs008_stcs_sale(extended_sell: float, revenue_share_pct: float) -> float:
    """
    STCS/distributor revenue share deduction.
    stcs_sale = extended_sell × (1 - revenue_share_pct)
    """
    result = _d(extended_sell) * (1 - _d(revenue_share_pct))
    return _round2(result)


def cs009_vat(amount: float, country_code: str,
               vat_rates: dict[str, dict]) -> tuple[float, float]:
    """
    Calculate VAT.
    Returns (vat_amount, vat_rate_used).
    vat_amount = amount × vat_rate
    """
    rate = _d(vat_rates.get(country_code, {}).get("rate", 0.0))
    vat_amount = _d(amount) * rate
    return _round2(vat_amount), float(rate)


# ---------------------------------------------------------------------------
# run_cost_stack — applies all steps to every matched line item
# ---------------------------------------------------------------------------

def run_cost_stack(summary: PricingSummary, config: dict) -> dict:
    """
    Apply CS-001 → CS-009 to all matched items in summary.

    Args:
        summary: PricingSummary from analyze_gaps (prices in USD)
        config:  Cost stack configuration dict (use load_defaults() as base)

    Returns:
        {
            "line_items": list[dict],   # per-line cost breakdown
            "summary": dict,            # totals
            "config_used": dict,        # echo of config
        }
    """
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
        list_usd = m.unit_price * qty  # line total in USD

        # CS-001
        list_local, fx_rate = cs001_currency_convert(list_usd, target_currency, fx_rates)
        unit_local = _round2(_d(list_local) / _d(qty))

        # CS-002
        after_discount = cs002_vendor_discount(list_local, vendor_discount_pct)

        # CS-003
        after_inhouse = cs003_inhouse_margin(after_discount, inhouse_margin_pct)

        # CS-004
        overhead_amt = cs004_overhead(after_inhouse, overhead_components)

        # CS-005
        cost_total = cs005_cost_with_overhead(after_inhouse, overhead_amt)

        # CS-006
        sell_price = cs006_selling_price(cost_total, selling_mode, selling_pct)

        # CS-007
        extended = cs007_extended_sell(sell_price, embed_discounts)

        # CS-008 (informational — actual STCS deduction at summary level only)
        stcs = cs008_stcs_sale(extended, revenue_share_pct)

        # CS-009 (per-line VAT)
        vat_amt, vat_rate = cs009_vat(extended, vat_country, vat_rates_data)
        total_with_vat = _round2(_d(extended) + _d(vat_amt))

        line_items.append({
            "sku": m.sku,
            "description": m.rfp_item.description,
            "qty": qty,
            "unit_list_usd": m.unit_price,
            "line_list_usd": _round2(_d(m.unit_price) * _d(qty)),
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

    # Summary-level CS-008
    stcs_total = cs008_stcs_sale(float(total_extended), revenue_share_pct)
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
```

---

## Step 4 — Update `backend/app/engines/e2/pipeline.py`

**Add import:**
```python
from .step6_cost_stack import run_cost_stack, load_defaults
```

**Add cost stack call** after `analyze_gaps` and before `write_output`. Find:

```python
    summary = analyze_gaps(matches)
    output_path = write_output(summary, template_path, detection)
```

Replace with:
```python
    summary = analyze_gaps(matches)

    # CS-001 → CS-009 cost stack
    cost_config = load_defaults()
    cost_stack_result = run_cost_stack(summary, cost_config)

    output_path = write_output(summary, template_path, detection,
                               cost_stack_result=cost_stack_result)
```

Also update the return dict to include cost stack summary:
```python
    return {
        "output_file": output_path,
        "distributor_file": distributor_path.name,
        "vendor_list": e1_output.vendor_list if e1_output else [],
        "requirements_baseline_count": len(e1_output.requirements_baseline) if e1_output else 0,
        "matched_count": len(summary.matched_items),
        "unmatched_count": len(summary.unmatched_items),
        "low_confidence_count": len(summary.low_confidence_items),
        "subtotal": summary.subtotal,
        "discount_amount": summary.discount_amount,
        "total": summary.total,
        "currency": summary.currency,
        "boq_items": boq_items,
        "eox_warnings": eox_warnings,
        "cost_stack": cost_stack_result["summary"],
    }
```

---

## Step 5 — Update `backend/app/engines/e2/step5_excel_writer.py`

Extend `write_output` to accept and write cost stack data.

**Change the function signature** from:
```python
def write_output(
    summary: PricingSummary,
    template_path: Path,
    detection: BoQDetectionResult,
) -> str:
```

To:
```python
def write_output(
    summary: PricingSummary,
    template_path: Path,
    detection: BoQDetectionResult,
    cost_stack_result: dict | None = None,
) -> str:
```

**Update `_HEADER_COLS`** to include cost stack columns when cost_stack_result is
provided. Inside `write_output`, after `_OUTPUT_DIR.mkdir(exist_ok=True)`, add:

```python
    has_cost_stack = bool(cost_stack_result and cost_stack_result.get("line_items"))
    currency = (cost_stack_result or {}).get("summary", {}).get("currency", "SAR") if has_cost_stack else "SAR"

    header_cols = _HEADER_COLS.copy()
    if has_cost_stack:
        header_cols += [
            f"List ({currency})",
            f"After Discount ({currency})",
            f"After Margin ({currency})",
            f"Overhead ({currency})",
            f"Cost+OH ({currency})",
            f"Sell Price ({currency})",
            f"Extended Sell ({currency})",
            f"VAT ({currency})",
            f"Total incl. VAT ({currency})",
        ]
```

**Update the header row write** to use `header_cols` instead of `_HEADER_COLS`:
```python
    for col, title in enumerate(header_cols, start=1):
        cell = ws.cell(row=header_row, column=col, value=title)
        cell.font = _BOLD
```

**Build a lookup dict for cost stack line items** (keyed by SKU) right before the
matched items loop:
```python
    cs_by_sku: dict[str, dict] = {}
    if has_cost_stack:
        for item in cost_stack_result["line_items"]:
            cs_by_sku[item["sku"]] = item
```

**After writing the 8 standard columns** for each matched item, append cost stack
columns if available:
```python
        for col, val in enumerate(
            [m.sku, m.rfp_item.description, qty, m.unit_price,
             f"{_SI_DISCOUNT:.0%}", line_total, m.match_method, m.match_score],
            start=1,
        ):
            ws.cell(row=row, column=col, value=val)

        # Cost stack columns
        if has_cost_stack and m.sku in cs_by_sku:
            cs = cs_by_sku[m.sku]
            col = 9
            for val in [
                cs["cs001_line_list_local"],
                cs["cs002_after_vendor_discount"],
                cs["cs003_after_inhouse_margin"],
                cs["cs004_overhead"],
                cs["cs005_cost_with_overhead"],
                cs["cs006_selling_price"],
                cs["cs007_extended_sell"],
                cs["cs009_vat"],
                cs["line_total_with_vat"],
            ]:
                cell = ws.cell(row=row, column=col, value=val)
                cell.alignment = _RIGHT
                col += 1

        row += 1
```

**Add cost stack summary block** after the existing summary block (after the
Subtotal/Discount/Total rows), still using `has_cost_stack`:

```python
    if has_cost_stack:
        cs_summary = cost_stack_result["summary"]
        row += 1  # spacer
        ws.cell(row=row, column=7, value=f"── Cost Stack Summary ({cs_summary['currency']}) ──").font = _BOLD
        row += 1
        for label, value in [
            (f"Total List ({cs_summary['currency']})", cs_summary["total_list_local"]),
            ("Total Cost (with OH)", cs_summary["total_cost"]),
            ("Total Sell Price", cs_summary["total_sell"]),
            (f"VAT ({cs_summary['vat_rate']:.0%})", cs_summary["total_vat"]),
            ("Total incl. VAT", cs_summary["total_with_vat"]),
            (f"STCS Sale ({cs_summary['vat_country']})", cs_summary["cs008_stcs_sale_total"]),
        ]:
            lc = ws.cell(row=row, column=7, value=label)
            lc.font = _BOLD
            lc.alignment = _RIGHT
            vc = ws.cell(row=row, column=8, value=f"{cs_summary['currency']} {value:,.2f}")
            vc.font = _BOLD
            vc.alignment = _RIGHT
            row += 1
```

---

## Step 6 — Update `backend/app/api/e2_routes.py`

**Store cost_stack summary** in step_outputs["e2"]. Find the `outputs['e2']` block
and add:
```python
                'cost_stack': result.get('cost_stack', {}),
```

---

## Step 7 — Validation steps

### 7A. JSON validity
```
backend\.venv\Scripts\python.exe -c "
import json
d = json.load(open('backend/app/engines/e2/data/cost_stack_defaults.json'))
assert 'target_currency' in d
assert 'overhead_components' in d
assert sum(d['overhead_components'].values()) > 0
print(f'Defaults: OK, overhead total = {sum(d[\"overhead_components\"].values()):.1%}')
"
```
Expected: `Defaults: OK, overhead total = 10.0%`

### 7B. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e2/step6_cost_stack.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e2/pipeline.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e2/step5_excel_writer.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e2_routes.py
```
Expected: no output.

### 7C. Pure function unit tests
```
backend\.venv\Scripts\python.exe -c "
from app.engines.e2.step6_cost_stack import (
    cs001_currency_convert, cs002_vendor_discount, cs003_inhouse_margin,
    cs004_overhead, cs005_cost_with_overhead, cs006_selling_price,
    cs007_extended_sell, cs008_stcs_sale, cs009_vat,
)

# CS-001: 1000 USD at SAR rate 3.75 = 3750
converted, rate = cs001_currency_convert(1000.0, 'SAR', {'SAR': 3.75})
assert converted == 3750.0, f'CS-001 failed: {converted}'
print('CS-001: PASS')

# CS-002: 30% discount off 3750 = 2625
after_disc = cs002_vendor_discount(3750.0, 0.30)
assert after_disc == 2625.0, f'CS-002 failed: {after_disc}'
print('CS-002: PASS')

# CS-003: 10% inhouse margin on 2625 = 2887.50
after_margin = cs003_inhouse_margin(2625.0, 0.10)
assert after_margin == 2887.50, f'CS-003 failed: {after_margin}'
print('CS-003: PASS')

# CS-004: 10% overhead on 2887.50 = 288.75
oh = cs004_overhead(2887.50, {'freight': 0.02, 'customs': 0.05, 'others': 0.03})
assert oh == 288.75, f'CS-004 failed: {oh}'
print('CS-004: PASS')

# CS-005: 2887.50 + 288.75 = 3176.25
cost_oh = cs005_cost_with_overhead(2887.50, 288.75)
assert cost_oh == 3176.25, f'CS-005 failed: {cost_oh}'
print('CS-005: PASS')

# CS-006 margin mode: 3176.25 / (1 - 0.25) = 4235.00
sell = cs006_selling_price(3176.25, 'margin', 0.25)
assert sell == 4235.0, f'CS-006 margin failed: {sell}'
print('CS-006 margin: PASS')

# CS-006 markup mode: 3176.25 * 1.25 = 3970.31
sell_mu = cs006_selling_price(3176.25, 'markup', 0.25)
assert sell_mu == 3970.31, f'CS-006 markup failed: {sell_mu}'
print('CS-006 markup: PASS')

# CS-007: no embed discounts = same as input
ext = cs007_extended_sell(4235.0, [])
assert ext == 4235.0, f'CS-007 no discount failed: {ext}'
ext2 = cs007_extended_sell(4235.0, [{'name': 'vol', 'pct': 0.05}])
assert ext2 == 4023.25, f'CS-007 with discount failed: {ext2}'
print('CS-007: PASS')

# CS-008: 5% revenue share off 4235 = 4023.25
stcs = cs008_stcs_sale(4235.0, 0.05)
assert stcs == 4023.25, f'CS-008 failed: {stcs}'
print('CS-008: PASS')

# CS-009: 15% VAT on 4235 = 635.25
vat, rate = cs009_vat(4235.0, 'SA', {'SA': {'rate': 0.15}})
assert vat == 635.25, f'CS-009 failed: {vat}'
assert rate == 0.15
print('CS-009: PASS')

print('All CS unit tests passed.')
"
```
Expected: 9 PASS lines then `All CS unit tests passed.`

### 7D. run_cost_stack integration test
```
backend\.venv\Scripts\python.exe -c "
from app.engines.e2.step6_cost_stack import run_cost_stack, load_defaults
from app.engines.e2.models import CatalogMatch, PricingSummary, RFPLineItem

config = load_defaults()
match = CatalogMatch(
    rfp_item=RFPLineItem('48-port PoE switch', 2.0, 'units', 'network', '', 0.9),
    sku='C9300-48P-E',
    product_name='Cisco Catalyst 9300',
    vendor='Cisco',
    unit_price=8500.0,
    match_score=1.0,
    match_method='exact',
)
summary = PricingSummary(
    matched_items=[match],
    unmatched_items=[],
    low_confidence_items=[],
    subtotal=17000.0,
    discount_amount=2550.0,
    total=14450.0,
)

result = run_cost_stack(summary, config)
assert len(result['line_items']) == 1
li = result['line_items'][0]
assert li['sku'] == 'C9300-48P-E'
assert li['currency'] == 'SAR'
assert li['cs001_line_list_local'] > 0
assert li['cs006_selling_price'] > li['cs005_cost_with_overhead']
assert li['line_total_with_vat'] > li['cs007_extended_sell']

s = result['summary']
assert s['total_with_vat'] > s['total_sell']
assert s['currency'] == 'SAR'
print(f'Sell: {s[\"currency\"]} {s[\"total_sell\"]:,.2f}  |  '
      f'VAT: {s[\"total_vat\"]:,.2f}  |  '
      f'Total: {s[\"total_with_vat\"]:,.2f}')
print('run_cost_stack: PASS')
"
```
Expected: a line with SAR amounts and `run_cost_stack: PASS`.

### 7E. Frontend/API are unchanged
```
cd frontend && npx tsc --noEmit && npm run build
```
Expected: zero errors (no frontend changes in this task).

---

## Step 8 — Summary of files changed

| Action   | File path                                            |
|----------|------------------------------------------------------|
| Created  | `backend/app/engines/e2/data/cost_stack_defaults.json` |
| Created  | `backend/app/engines/e2/step6_cost_stack.py`         |
| Modified | `backend/app/engines/e2/pipeline.py`                 |
| Modified | `backend/app/engines/e2/step5_excel_writer.py`       |
| Modified | `backend/app/api/e2_routes.py`                       |

No DB migration. No frontend changes. No new pip dependencies.

---

## Step 9 — Git commit message

```
feat: implement E2 cost stack CS-001 through CS-009

- cost_stack_defaults.json: default config (SAR target, 30% vendor
  discount, 10% inhouse margin, 10% overhead, 25% gross margin,
  5% STCS share, 15% SA VAT)

- step6_cost_stack.py: pure Decimal-arithmetic functions for each step
  cs001_currency_convert, cs002_vendor_discount, cs003_inhouse_margin,
  cs004_overhead, cs005_cost_with_overhead, cs006_selling_price (margin
  and markup modes), cs007_extended_sell, cs008_stcs_sale, cs009_vat
  run_cost_stack(summary, config) applies all steps to every matched item

- pipeline.py: call run_cost_stack after analyze_gaps; pass result to
  write_output; add cost_stack summary to pipeline result dict

- step5_excel_writer.py: write_output now accepts optional cost_stack_result;
  adds 9 cost stack columns to matched item rows; adds cost stack summary
  block below the existing subtotal/discount/total rows

- e2_routes.py: store cost_stack summary in step_outputs["e2"]["cost_stack"]
```
