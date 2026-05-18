from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from .models import BoQDetectionResult, PricingSummary

_OUTPUT_DIR = Path(__file__).parent / "output"
_SI_DISCOUNT = 0.15

_HEADER_COLS = [
    "Part Number", "Description", "Qty", "Unit Price",
    "Discount %", "Line Total", "Match Method", "Match Score",
]

_BOLD = Font(bold=True)
_BOLD_WHITE = Font(bold=True, color="FFFFFF")
_RIGHT = Alignment(horizontal="right")
_RED_FILL = PatternFill(fill_type="solid", fgColor="FF0000")


def write_output(
    summary: PricingSummary,
    template_path: Path,
    detection: BoQDetectionResult,
) -> str:
    _OUTPUT_DIR.mkdir(exist_ok=True)
    stem = Path(template_path).stem
    output_path = _OUTPUT_DIR / f"{stem}_BOMATIC_filled.xlsx"

    wb = openpyxl.load_workbook(template_path)
    ws = wb[detection.sheet_name]

    # detection.header_row_index is 0-based; openpyxl rows are 1-based
    header_row = detection.header_row_index + 1

    # Write our column headers over the template's original header row
    for col, title in enumerate(_HEADER_COLS, start=1):
        cell = ws.cell(row=header_row, column=col, value=title)
        cell.font = _BOLD

    # Find the first empty data row after the header
    row = _first_empty_row(ws, header_row + 1)

    # --- Matched items ---
    for m in summary.matched_items:
        qty = m.rfp_item.quantity if m.rfp_item.quantity is not None else 1.0
        line_total = round(qty * m.unit_price * (1 - _SI_DISCOUNT), 2)
        for col, val in enumerate(
            [m.sku, m.rfp_item.description, qty, m.unit_price,
             f"{_SI_DISCOUNT:.0%}", line_total, m.match_method, m.match_score],
            start=1,
        ):
            ws.cell(row=row, column=col, value=val)
        row += 1

    row += 1  # blank separator

    # --- Unmatched items (NEEDS REVIEW) ---
    for m in summary.unmatched_items:
        review_cell = ws.cell(row=row, column=1, value="NEEDS REVIEW")
        review_cell.fill = _RED_FILL
        review_cell.font = _BOLD_WHITE
        ws.cell(row=row, column=2, value=m.rfp_item.description)
        if m.rfp_item.quantity is not None:
            ws.cell(row=row, column=3, value=m.rfp_item.quantity)
        ws.cell(row=row, column=7, value="unmatched")
        row += 1

    row += 1  # blank separator before summary

    # --- Summary block (columns G–H, bold + right-aligned) ---
    for label, value in [
        ("Subtotal", summary.subtotal),
        (f"Discount Amount ({_SI_DISCOUNT:.0%})", summary.discount_amount),
        ("Total", summary.total),
    ]:
        label_cell = ws.cell(row=row, column=7, value=label)
        label_cell.font = _BOLD
        label_cell.alignment = _RIGHT

        value_cell = ws.cell(row=row, column=8, value=f"{summary.currency} {value:,.2f}")
        value_cell.font = _BOLD
        value_cell.alignment = _RIGHT
        row += 1

    wb.save(output_path)
    return str(output_path)


def _first_empty_row(ws, from_row: int) -> int:
    """Return the first 1-based row index (>= from_row) where all cells are empty."""
    for idx, row in enumerate(ws.iter_rows(min_row=from_row, values_only=True), start=from_row):
        if all(v is None for v in row):
            return idx
    return ws.max_row + 1


if __name__ == "__main__":
    from app.engines.e2.models import CatalogMatch, RFPLineItem
    from app.engines.e2.step4_gap_analyzer import analyze_gaps

    matches = [
        CatalogMatch(
            rfp_item=RFPLineItem(description="Cisco ASA 5516-X firewall", quantity=2, unit="units", category="security", raw_text="", confidence=0.9),
            sku="ASA5516-FPWR-K9", product_name="Cisco ASA 5516-X with FirePOWER Services",
            vendor="Cisco", unit_price=4995.00, match_score=1.0, match_method="exact",
        ),
        CatalogMatch(
            rfp_item=RFPLineItem(description="48-port PoE+ switch", quantity=10, unit="units", category="network", raw_text="", confidence=0.85),
            sku="C9300-48P-E", product_name="Cisco Catalyst 9300 48-Port PoE+ Switch",
            vendor="Cisco", unit_price=7200.00, match_score=0.55, match_method="fuzzy",
        ),
        CatalogMatch(
            rfp_item=RFPLineItem(description="unmanaged desktop hub", quantity=1, unit="units", category="hardware", raw_text="", confidence=0.6),
            sku="", product_name="", vendor="", unit_price=0.0, match_score=0.0, match_method="unmatched",
        ),
    ]

    summary = analyze_gaps(matches)

    fixture = Path(__file__).parents[3] / "storage" / "e1_test_fixtures" / "BOQ_4203193153.xlsx"
    from app.engines.e2.step1_template_detector import detect_template
    detection = detect_template(fixture)

    out = write_output(summary, fixture, detection)
    print(f"Written: {out}")
