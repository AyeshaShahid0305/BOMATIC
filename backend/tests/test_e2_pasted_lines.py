import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engines.e2.models import BoQDetectionResult, CatalogMatch
from app.engines.e2.pasted_line_parser import parse_pasted_line_items
from app.engines.e2.pipeline import run_e2_pipeline


def test_pasted_text_produces_non_zero_requirements():
    items = parse_pasted_line_items(
        "2, Cisco Catalyst 9300 switch\n5\tWireless access point"
    )

    assert len(items) == 2
    assert items[0].quantity == 2
    assert items[1].description == "Wireless access point"


def test_e2_matching_runs_against_pasted_items(tmp_path, monkeypatch):
    template_path = tmp_path / "template.xlsx"
    template_path.write_bytes(b"test")
    output_path = tmp_path / "priced.xlsx"
    distributor_path = tmp_path / "distributor.xlsx"

    monkeypatch.setattr(
        "app.engines.e2.pipeline.extract_rfp_requirements",
        lambda _text: (_ for _ in ()).throw(
            AssertionError("RFP extraction must be bypassed")
        ),
    )
    monkeypatch.setattr(
        "app.engines.e2.pipeline.detect_template",
        lambda _path: BoQDetectionResult(
            format_type="UNKNOWN",
            confidence=1.0,
            sheet_name="Sheet1",
            header_row_index=0,
        ),
    )
    monkeypatch.setattr("app.engines.e2.pipeline.parse_boq", lambda _path, _detection: [])

    def match_pasted_items(items, vendor_list=None):
        assert vendor_list is None
        assert len(items) == 1
        assert items[0].quantity == 2
        assert items[0].description == "Cisco Catalyst 9300 switch"
        return [
            CatalogMatch(
                rfp_item=items[0],
                sku="C9300-48P-E",
                product_name="Cisco Catalyst 9300 48-Port PoE+ Switch",
                vendor="Cisco",
                unit_price=7200,
                match_score=1.0,
                match_method="exact",
            )
        ]

    monkeypatch.setattr("app.engines.e2.pipeline.match_catalog", match_pasted_items)
    monkeypatch.setattr("app.engines.e2.pipeline.check_eox", lambda _skus: [])
    monkeypatch.setattr(
        "app.engines.e2.pipeline.run_cost_stack",
        lambda _summary, _config: {"summary": {}},
    )
    monkeypatch.setattr(
        "app.engines.e2.pipeline.write_output",
        lambda *_args, **_kwargs: output_path,
    )
    monkeypatch.setattr(
        "app.engines.e2.pipeline.write_distributor_export",
        lambda *_args, **_kwargs: distributor_path,
    )

    result = run_e2_pipeline(
        "",
        template_path,
        pasted_text="2, Cisco Catalyst 9300 switch",
        cost_config={},
    )

    assert result["requirement_input_count"] == 1
    assert result["matched_count"] == 1
    assert result["pricing_artifact"]["matched_items"][0]["quantity"] == 2
