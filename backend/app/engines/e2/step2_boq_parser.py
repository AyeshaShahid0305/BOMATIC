import re
from pathlib import Path

import openpyxl

from .models import BoQDetectionResult, BoQLineItem
from .step1_template_detector import (
    FORMAT_1_CCW,
    FORMAT_2_ARAMCO_2022,
    FORMAT_2_ARAMCO_2024,
    FORMAT_3_NTT,
    UNKNOWN,
)

_CISCO_SKU_RE = re.compile(r"^[A-Z][A-Z0-9]{1,}-[A-Z0-9]")

COLUMN_MAPPINGS = {
    FORMAT_1_CCW: {"part_number": 0, "description": 1, "qty": 2, "unit_price": 3, "total_price": 4},
    FORMAT_2_ARAMCO_2022: {"part_number": 1, "description": 2, "qty": 3, "unit_price": 4, "total_price": 5},
    FORMAT_2_ARAMCO_2024: {"part_number": 2, "description": 3, "qty": 4, "unit_price": 5, "total_price": 6},
    FORMAT_3_NTT: {"part_number": 1, "description": 2, "qty": 3, "unit_price": 4, "total_price": 6},
    UNKNOWN: {"part_number": 0, "description": 1, "qty": 2, "unit_price": 3, "total_price": 4},
}


def _mapped_value(row: tuple, mapping: dict[str, int], field: str):
    index = mapping[field]
    return row[index] if index < len(row) else None


def _number(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, str):
        value = value.replace(",", "").replace("$", "").strip()
    return float(value)


def parse(file_path: Path, detection: BoQDetectionResult) -> list[BoQLineItem]:
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    try:
        ws = wb[detection.sheet_name]

        rows = ws.iter_rows(values_only=True)

        # Skip rows up to and including the header
        for _ in range(detection.header_row_index + 1):
            next(rows)

        mapping = COLUMN_MAPPINGS.get(detection.format_type, COLUMN_MAPPINGS[UNKNOWN])
        items = []
        for row in rows:
            part_number = _mapped_value(row, mapping, "part_number")
            description = _mapped_value(row, mapping, "description")
            qty = _mapped_value(row, mapping, "qty")
            unit_price = _mapped_value(row, mapping, "unit_price")
            total_price = _mapped_value(row, mapping, "total_price")

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
                qty=int(_number(qty)),
                unit_price_usd=_number(unit_price),
                total_price_usd=_number(total_price),
                line_type=line_type,
            ))
    finally:
        wb.close()

    return items


if __name__ == "__main__":
    from app.engines.e2.step1_template_detector import detect_template

    fixture = Path(__file__).parents[3] / "storage" / "e1_test_fixtures" / "BOQ_4203193153.xlsx"
    detection = detect_template(fixture)
    print(f"Detected: {detection}\n")
    for item in parse(fixture, detection):
        print(item)
