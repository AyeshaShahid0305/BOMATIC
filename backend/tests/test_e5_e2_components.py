import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engines.e2.models import BoQDetectionResult, CatalogMatch
from app.engines.e2.pipeline import run_e2_pipeline
from app.engines.e5.models import DesignSection
from app.engines.e5.pipeline import run_e5_pipeline
from app.schemas.pipeline import E5Component, E5ComponentArtifact


def test_e5_pipeline_returns_non_empty_component_list(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.engines.e5.pipeline.read_context",
        lambda _session_id, _db: {
            "project_name": "Component Test",
            "has_e1_data": True,
        },
    )
    monkeypatch.setattr(
        "app.engines.e5.pipeline.generate_hld",
        lambda _context: [
            DesignSection(
                id="HLD-003",
                title="High Level Topology",
                content="The solution uses two core switches and redundant firewalls.",
                level="HLD",
                order=3,
            )
        ],
    )
    monkeypatch.setattr(
        "app.engines.e5.pipeline.generate_lld",
        lambda _context, _hld: [
            DesignSection(
                id="LLD-002",
                title="Device Roles",
                content="Access switches provide connectivity for endpoint devices.",
                level="LLD",
                order=2,
            )
        ],
    )
    output_path = tmp_path / "design.docx"
    output_path.write_bytes(b"test")
    monkeypatch.setattr(
        "app.engines.e5.pipeline.write_design_document",
        lambda _document: output_path,
    )

    result = run_e5_pipeline("OPP-COMPONENTS", db=None)

    artifact = E5ComponentArtifact.model_validate(result["component_artifact"])
    assert result["components"]
    assert artifact.components


def test_e2_consumes_e5_components_into_matched_items(tmp_path, monkeypatch):
    template_path = tmp_path / "template.xlsx"
    template_path.write_bytes(b"test")
    output_path = tmp_path / "priced.xlsx"
    distributor_path = tmp_path / "distributor.xlsx"
    artifact = E5ComponentArtifact(
        components=[
            E5Component(
                description="Cisco Catalyst 9300 switch",
                quantity=2,
                category="network",
            )
        ]
    )

    monkeypatch.setattr(
        "app.engines.e2.pipeline.detect_template",
        lambda _path: BoQDetectionResult(
            format_type="generic",
            confidence=1.0,
            sheet_name="Sheet1",
            header_row_index=0,
        ),
    )
    monkeypatch.setattr("app.engines.e2.pipeline.parse_boq", lambda _path, _detection: [])

    def match_components(items, vendor_list=None):
        assert vendor_list is None
        assert any(item.description == "Cisco Catalyst 9300 switch" for item in items)
        return [
            CatalogMatch(
                rfp_item=item,
                sku="C9300-48P-E",
                product_name="Cisco Catalyst 9300 48-Port PoE+ Switch",
                vendor="Cisco",
                unit_price=7200,
                match_score=1.0,
                match_method="exact",
            )
            for item in items
        ]

    monkeypatch.setattr("app.engines.e2.pipeline.match_catalog", match_components)
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
        e5_components=artifact,
        cost_config={},
    )

    pricing = result["pricing_artifact"]
    assert result["matched_count"] == 1
    assert pricing["matched_items"][0]["description"] == "Cisco Catalyst 9300 switch"
