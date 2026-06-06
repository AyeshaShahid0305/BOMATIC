import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openpyxl import Workbook

from app.engines.e2.step1_template_detector import (
    FORMAT_1_CCW,
    FORMAT_2_ARAMCO_2022,
    FORMAT_2_ARAMCO_2024,
    detect_template,
)
from app.engines.e2.step2_boq_parser import parse


def _write_workbook(path, sheet_name, headers, row):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(headers)
    worksheet.append(row)
    workbook.save(path)


def test_parse_ccw_uses_ccw_columns(tmp_path):
    path = tmp_path / "ccw.xlsx"
    _write_workbook(
        path,
        "Main BOQ",
        ["Part Number", "Description", "Qty", "Unit Price (USD)", "Total Price (USD)"],
        ["C9300-48P-E", "Cisco Catalyst 9300", 2, 7200, 14400],
    )

    detection = detect_template(path)
    items = parse(path, detection)

    assert detection.format_type == FORMAT_1_CCW
    assert items[0].part_number == "C9300-48P-E"
    assert items[0].description == "Cisco Catalyst 9300"
    assert items[0].qty == 2
    assert items[0].unit_price_usd == 7200


def test_parse_aramco_2022_uses_unshifted_columns(tmp_path):
    path = tmp_path / "aramco_2022.xlsx"
    _write_workbook(
        path,
        "Price Schedule",
        ["Line", "Material Number", "Item Description", "Quantity", "Unit Rate", "Amount"],
        [1, "ASA5516-FPWR-K9", "Cisco ASA Firewall", 3, 5000, 15000],
    )

    detection = detect_template(path)
    items = parse(path, detection)

    assert detection.format_type == FORMAT_2_ARAMCO_2022
    assert items[0].part_number == "ASA5516-FPWR-K9"
    assert items[0].description == "Cisco ASA Firewall"
    assert items[0].qty == 3
    assert items[0].total_price_usd == 15000


def test_parse_aramco_2024_applies_shifted_columns(tmp_path):
    path = tmp_path / "aramco_2024.xlsx"
    _write_workbook(
        path,
        "Price Schedule",
        ["Line", "Item No", "Material Number", "Item Description", "Quantity", "Unit Rate", "Amount"],
        [1, 10, "C9300-48P-E", "Cisco Catalyst 9300", 4, 7200, 28800],
    )

    detection = detect_template(path)
    items = parse(path, detection)

    assert detection.format_type == FORMAT_2_ARAMCO_2024
    assert items[0].part_number == "C9300-48P-E"
    assert items[0].description == "Cisco Catalyst 9300"
    assert items[0].qty == 4
    assert items[0].unit_price_usd == 7200
