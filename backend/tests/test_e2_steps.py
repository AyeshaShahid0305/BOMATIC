import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.engines.e2.models import CatalogMatch, RFPLineItem
from app.engines.e2.step3_catalog_matcher import match_catalog
from app.engines.e2.step4_gap_analyzer import analyze_gaps

_MINIMAL_CATALOG = [
    {
        "sku": "C9300-48P-E",
        "product_name": "Cisco Catalyst 9300 48-Port PoE+ Switch",
        "vendor": "Cisco",
        "unit_price": 7200.00,
        "category": "network",
        "keywords": ["switch", "catalyst", "poe", "48-port"],
    }
]


# ---------------------------------------------------------------------------
# Step 3 — match_catalog
# ---------------------------------------------------------------------------

def test_step3_matches_known_item(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(json.dumps(_MINIMAL_CATALOG), encoding="utf-8")

    items = [RFPLineItem(
        description="Cisco Catalyst 9300 switch",
        quantity=2,
        unit="units",
        category="network",
        raw_text="",
        confidence=0.9,
    )]
    result = match_catalog(items, catalog_path=catalog_file)

    assert len(result) == 1
    assert result[0].match_method != "unmatched"


def test_step3_gibberish_returns_unmatched(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(json.dumps(_MINIMAL_CATALOG), encoding="utf-8")

    items = [RFPLineItem(
        description="xyzzy foobar 99999",
        quantity=1,
        unit="units",
        category="unknown",
        raw_text="",
        confidence=0.5,
    )]
    result = match_catalog(items, catalog_path=catalog_file)

    assert len(result) == 1
    assert result[0].match_method == "unmatched"


# ---------------------------------------------------------------------------
# Step 4 — analyze_gaps
# ---------------------------------------------------------------------------

def _make_rfp_item(description: str = "test item", quantity: float = 1.0) -> RFPLineItem:
    return RFPLineItem(
        description=description,
        quantity=quantity,
        unit="units",
        category="network",
        raw_text="",
        confidence=0.9,
    )


def test_step4_buckets_and_discount():
    matched_item = CatalogMatch(
        rfp_item=_make_rfp_item(quantity=1.0),
        sku="C9300-48P-E",
        product_name="Cisco Catalyst 9300",
        vendor="Cisco",
        unit_price=1000.0,
        match_score=0.9,
        match_method="fuzzy",
    )
    low_conf_item = CatalogMatch(
        rfp_item=_make_rfp_item(),
        sku="SOME-SKU",
        product_name="Some Product",
        vendor="Vendor",
        unit_price=500.0,
        match_score=0.49,
        match_method="fuzzy",
    )

    summary = analyze_gaps([matched_item, low_conf_item])

    assert len(summary.matched_items) == 1
    assert len(summary.low_confidence_items) == 1
    assert len(summary.unmatched_items) == 0
    assert summary.total < summary.subtotal  # SI discount applied
    assert isinstance(summary.subtotal, float)


def test_step4_unmatched_item_lands_in_unmatched_bucket():
    unmatched_item = CatalogMatch(
        rfp_item=_make_rfp_item(),
        sku="",
        product_name="",
        vendor="",
        unit_price=0.0,
        match_score=0.0,
        match_method="unmatched",
    )

    summary = analyze_gaps([unmatched_item])

    assert len(summary.unmatched_items) == 1
    assert len(summary.matched_items) == 0
    assert len(summary.low_confidence_items) == 0
