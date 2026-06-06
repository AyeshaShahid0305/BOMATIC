import csv
from io import StringIO

from .models import RFPLineItem


def parse_pasted_line_items(text: str) -> list[RFPLineItem]:
    items: list[RFPLineItem] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        delimiter = "\t" if "\t" in line else ","
        fields = next(csv.reader(StringIO(line), delimiter=delimiter))
        fields = [field.strip() for field in fields]
        if len(fields) < 2:
            continue

        try:
            quantity = float(fields[0])
        except ValueError:
            continue

        description = delimiter.join(fields[1:]).strip()
        if not description or quantity <= 0:
            continue

        items.append(
            RFPLineItem(
                description=description,
                quantity=quantity,
                unit="units",
                category="hardware",
                raw_text=raw_line,
                confidence=1.0,
            )
        )
    return items
