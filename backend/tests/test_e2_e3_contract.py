import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi import HTTPException

from app.api.e3_routes import _load_pricing_artifact
from app.schemas.pipeline import E2PricingArtifact, E2PricingLine


def test_persisted_e2_dictionary_loads_as_pricing_artifact():
    persisted = {
        "artifact_type": "e2_pricing",
        "schema_version": 1,
        "matched_items": [
            {
                "sku": "TEST-SKU",
                "product_name": "Test Product",
                "description": "Test switch",
                "quantity": 2,
                "unit_price": 1000,
            }
        ],
        "subtotal": 2000,
        "discount_amount": 300,
        "total": 1700,
        "currency": "USD",
        "output_file": "priced.xlsx",
    }

    artifact = _load_pricing_artifact(persisted)

    assert isinstance(artifact, E2PricingArtifact)
    assert artifact.total == 1700
    assert artifact.matched_items[0].quantity == 2


def test_legacy_e2_dictionary_loads_with_empty_line_items():
    artifact = _load_pricing_artifact(
        {
            "subtotal": 1000,
            "discount_amount": 150,
            "total": 850,
            "currency": "USD",
        }
    )

    assert artifact.schema_version == 1
    assert artifact.total == 850
    assert artifact.matched_items == []


def test_invalid_e2_dictionary_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        _load_pricing_artifact({"total": -1, "currency": "USD"})

    assert exc_info.value.status_code == 409


def test_e2_persisted_blob_round_trips_into_e3_pricing_artifact():
    pricing_artifact = E2PricingArtifact(
        matched_items=[
            E2PricingLine(
                sku="TEST-SKU",
                product_name="Test Product",
                description="Test switch",
                quantity=2,
                unit_price=1000,
            )
        ],
        subtotal=2000,
        discount_amount=300,
        total=1700,
        currency="USD",
    )
    result = {
        "matched_count": 1,
        "unmatched_count": 0,
        "low_confidence_count": 0,
        "vendor_list": ["Cisco"],
        "output_file": "priced.xlsx",
        "eox_warnings": [],
        "cost_stack": {"selling_price": 1700},
    }
    persisted_e2 = {
        **pricing_artifact.model_dump(mode="json"),
        "matched_count": result["matched_count"],
        "unmatched_count": result["unmatched_count"],
        "low_confidence_count": result["low_confidence_count"],
        "vendor_list": result["vendor_list"],
        "output_file": result["output_file"],
        "eox_warnings": result["eox_warnings"],
        "cost_stack": result["cost_stack"],
        "cost_config": {},
    }

    artifact = _load_pricing_artifact(persisted_e2)

    assert artifact.total > 0
    assert len(artifact.matched_items) > 0
