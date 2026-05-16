import re
from pathlib import Path

import openpyxl

from .models import BoQDetectionResult, BoQLineItem

_CISCO_SKU_RE = re.compile(r"^[A-Z][A-Z0-9]{1,}-[A-Z0-9]")


def parse(file_path: Path, detection: BoQDetectionResult) -> list[BoQLineItem]:
    with openpyxl.load_workbook(file_path, read_only=True, data_only=True) as wb:
        ws = wb[detection.sheet_name]

        rows = ws.iter_rows(values_only=True)

        # Skip rows up to and including the header
        for _ in range(detection.header_row_index + 1):
            next(rows)

        items = []
        for row in rows:
            part_number, description, qty, unit_price, total_price = (row + (None,) * 5)[:5]

            # Stop at first fully empty row
            if all(v is None for v in (part_number, description, qty, unit_price, total_price)):
                break

            # Skip section-header / subtotal rows (no part number and no qty)
            if part_number is None and qty is None:
                continue

            line_type = (
                "product"
                if part_number and _CISCO_SKU_RE.match(str(part_number))
                else "service"
            )

            items.append(BoQLineItem(
                part_number=str(part_number) if part_number is not None else "",
                description=str(description) if description is not None else "",
                qty=int(float(qty)) if qty is not None else 0,
                unit_price_usd=float(unit_price) if unit_price is not None else 0.0,
                total_price_usd=float(total_price) if total_price is not None else 0.0,
                line_type=line_type,
            ))

    return items


if __name__ == "__main__":
    from app.engines.e2.step1_template_detector import detect_template

    fixture = Path(__file__).parents[3] / "storage" / "e1_test_fixtures" / "BOQ_4203193153.xlsx"
    detection = detect_template(fixture)
    print(f"Detected: {detection}\n")
    for item in parse(fixture, detection):
        print(item)
