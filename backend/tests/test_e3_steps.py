import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.engines.e2.models import CatalogMatch, PricingSummary, RFPLineItem
from app.engines.e3.step1_template_selector import select_template
from app.engines.e3.step3_e2_data_reader import read_e2_data
from app.engines.e3.step4_narrative_generator import generate_narratives
from app.engines.e3.step5_assembler import assemble_proposal
from app.engines.e3.step8_gbb_pricing import calculate_gbb


# ---------------------------------------------------------------------------
# select_template
# ---------------------------------------------------------------------------

def test_select_template_returns_15_sections():
    sections = select_template("rfp")
    assert isinstance(sections, list)
    assert len(sections) == 15


def test_select_template_has_ai_generated_sections():
    sections = select_template("rfp")
    assert any(s.ai_generated for s in sections)


def test_select_template_all_titles_non_empty():
    sections = select_template("rfp")
    assert all(s.title for s in sections)


# ---------------------------------------------------------------------------
# read_e2_data
# ---------------------------------------------------------------------------

def test_read_e2_data_returns_expected_structure():
    rfp_item = RFPLineItem(
        description="Test switch",
        quantity=1.0,
        unit="units",
        category="network",
        raw_text="",
        confidence=0.9,
    )
    match = CatalogMatch(
        rfp_item=rfp_item,
        sku="TEST-SKU",
        product_name="Test Product",
        vendor="Cisco",
        unit_price=1000.0,
        match_score=0.9,
        match_method="fuzzy",
    )
    summary = PricingSummary(
        matched_items=[match],
        unmatched_items=[],
        low_confidence_items=[],
        subtotal=1000.0,
        discount_amount=150.0,
        total=850.0,
    )

    result = read_e2_data(summary)

    assert isinstance(result, dict)
    assert "matched_items" in result
    assert "subtotal" in result
    assert "total" in result
    assert len(result["matched_items"]) == 1


# ---------------------------------------------------------------------------
# calculate_gbb
# ---------------------------------------------------------------------------

def test_calculate_gbb_good_tier():
    result = calculate_gbb(1000.0, "good")
    assert result.adjusted_price == 1000.0


def test_calculate_gbb_better_tier():
    result = calculate_gbb(1000.0, "better")
    assert result.adjusted_price == 1325.0


def test_calculate_gbb_best_tier():
    result = calculate_gbb(1000.0, "best")
    assert result.adjusted_price == 1800.0


def test_calculate_gbb_unknown_tier_raises():
    with pytest.raises(ValueError):
        calculate_gbb(1000.0, "unknown")


# ---------------------------------------------------------------------------
# assemble_proposal
# ---------------------------------------------------------------------------

def test_assemble_proposal_returns_sections_with_title_and_content(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    sections = select_template("rfp")
    e1_data = {
        "project_name": "Test Project",
        "requirements": [],
        "legal_traps": [],
        "missing_documents": [],
        "rfp_text": "",
    }
    e2_data = {
        "matched_items": [],
        "unmatched_items": [],
        "subtotal": 0.0,
        "discount_amount": 0.0,
        "total": 0.0,
        "currency": "USD",
    }
    gbb_result = calculate_gbb(0.0, "better")
    narratives = generate_narratives(e1_data, e2_data, sections, gbb_tier="better")

    assembled = assemble_proposal(sections, narratives, e1_data, e2_data, gbb_result)

    assert isinstance(assembled, list)
    assert len(assembled) == len(sections)
    assert all("title" in s for s in assembled)
    assert all("content" in s for s in assembled)
