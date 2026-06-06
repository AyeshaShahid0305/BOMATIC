import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.engines.e2.models import RFPLineItem
from app.engines.e2.step3_catalog_matcher import match_catalog


def _rfp_item(description):
    return RFPLineItem(
        description=description,
        quantity=1,
        unit="units",
        category="network",
        raw_text=description,
        confidence=1.0,
    )


def test_catalog_environment_override_loads_alternative_source(tmp_path, monkeypatch):
    catalog_path = tmp_path / "governed_catalog.json"
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "sku": "GOV-SWITCH-01",
                    "product_name": "Governed Datacenter Switch",
                    "vendor": "Governed Vendor",
                    "unit_price": 1234.5,
                    "category": "network",
                    "keywords": ["governed", "datacenter", "switch"],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CATALOG_DATA_SOURCE", str(catalog_path))
    get_settings.cache_clear()

    try:
        matches = match_catalog([_rfp_item("GOV-SWITCH-01 governed datacenter switch")])
    finally:
        get_settings.cache_clear()

    assert matches[0].sku == "GOV-SWITCH-01"
    assert matches[0].unit_price == 1234.5


def test_stale_catalog_source_emits_warning(tmp_path, caplog):
    catalog_path = tmp_path / "stale_catalog.json"
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "sku": "STALE-SWITCH-01",
                    "product_name": "Stale Switch",
                    "vendor": "Vendor",
                    "unit_price": 100,
                    "category": "network",
                    "keywords": ["stale", "switch"],
                }
            ]
        ),
        encoding="utf-8",
    )
    stale_time = (
        datetime.now(timezone.utc) - timedelta(days=31)
    ).timestamp()
    os.utime(catalog_path, (stale_time, stale_time))

    with caplog.at_level(logging.WARNING, logger="app.engines.e2.data_sources"):
        match_catalog([_rfp_item("STALE-SWITCH-01")], catalog_path=catalog_path)

    assert "Catalog data source is stale" in caplog.text
    assert "31 days old" in caplog.text
