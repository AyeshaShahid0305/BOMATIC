import json
from pathlib import Path

import pytest

from app.engines.e1.step1_classifier import classify_file

# Navigate from this file up 4 parents to reach backend/, then into fixtures.
BACKEND = Path(__file__).resolve().parents[4]
FIXTURES = BACKEND / "storage" / "e1_test_fixtures"


def test_all_fixtures_meet_expected_type():
    entries = json.loads((FIXTURES / "manual_classification.json").read_text())
    for entry in entries:
        result = classify_file(entry["filename"])
        print(f"\n  {result.confidence:.2f} {result.type}/{result.subtype} <- {entry['filename']}")
        assert result.type == entry["expected_type"], (
            f"{entry['filename']}: expected type={entry['expected_type']!r}, got {result.type!r}"
        )


def test_all_fixtures_meet_min_confidence():
    entries = json.loads((FIXTURES / "manual_classification.json").read_text())
    for entry in entries:
        result = classify_file(entry["filename"])
        assert result.confidence >= entry["min_confidence"], (
            f"{entry['filename']}: expected min_confidence={entry['min_confidence']}, "
            f"got {result.confidence:.2f}"
        )


def test_folder_fallback():
    result = classify_file("Document_001.pdf", "BOQ/Pricing")
    assert result.type == "commercial"
    assert result.stage_used == "folder"


def test_content_fallback():
    file_path = FIXTURES / "Technical_Bid_Requirements.pdf"
    result = classify_file("document.pdf", "", file_path)
    assert result.type == "technical"


def test_cannot_auto_process_never_opens_file():
    result = classify_file("blueprint.dwg", "", Path("nonexistent/path.dwg"))
    assert result.can_auto_process is False


def test_low_confidence_flagged(tmp_path):
    f = tmp_path / "misc.dat"
    f.write_bytes(b"random binary content xyz")
    result = classify_file("misc.dat", "", f)
    assert result.needs_human_review is True
