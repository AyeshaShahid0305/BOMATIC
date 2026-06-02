import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from app.engines.e1.models import Classification, Requirement, RiskFlag
from app.main import app
from app.schemas.pipeline import E1Output


FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_RFP_TEXT = (FIXTURE_DIR / "sample_rfp_test.txt").read_text(encoding="utf-8")


def test_e1_outputs_endpoint_returns_valid_handoff(monkeypatch):
    opportunity_id = f"PIPE-{uuid.uuid4().hex[:8].upper()}"
    client = TestClient(app)
    headers = {"X-API-Key": "bomatic-dev-key"}

    imported = E1Output(
        vendor_list=["Cisco"],
        requirements_baseline=[{"id": "REQ-001", "text": "Cisco firewall required"}],
        risk_flags=[],
        sector="",
        frameworks_selected=[],
    )
    assert isinstance(imported.vendor_list, list)
    assert isinstance(imported.requirements_baseline, list)
    assert isinstance(imported.risk_flags, list)
    assert isinstance(imported.sector, str)
    assert isinstance(imported.frameworks_selected, list)

    before = client.get(f"/api/pipeline/{opportunity_id}/e1-outputs", headers=headers)
    assert before.status_code == 404

    monkeypatch.setattr(
        "app.api.e1_router.extract_text",
        lambda _path: {"text": SAMPLE_RFP_TEXT, "error": None, "can_auto_process": True},
    )
    monkeypatch.setattr(
        "app.api.e1_router.classify_file",
        lambda **_kwargs: Classification(
            type="rfp",
            subtype="main",
            confidence=0.95,
            stage_used="test",
        ),
    )
    monkeypatch.setattr(
        "app.api.e1_router.extract_requirements",
        lambda _texts, opportunity_id: [
            Requirement(
                id="REQ-001",
                text="The Vendor shall supply Cisco ASA 5516-X firewalls with FirePOWER Services.",
                classification="mandatory",
                confidence=0.95,
                source_file="sample_rfp.pdf",
                page=1,
            )
        ],
    )
    monkeypatch.setattr(
        "app.api.e1_router.detect_legal_traps",
        lambda _texts: [
            RiskFlag(
                flag="Unlimited liability clause detected.",
                severity="high",
                source="sample_rfp.pdf",
            )
        ],
    )
    monkeypatch.setattr(
        "app.api.e1_router.detect_missing_documents",
        lambda _classified, _texts: [],
    )
    monkeypatch.setattr(
        "app.api.e1_router.extract_evaluation_criteria",
        lambda _texts: [],
    )

    response = client.post(
        "/api/v1/rfp/packages",
        data={"opportunity_id": opportunity_id, "project_name": "Pipeline Handoff Test"},
        files={"files": ("sample_rfp.pdf", SAMPLE_RFP_TEXT.encode("utf-8"), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    run = client.post(f"/api/e1/{opportunity_id}/run", headers=headers)
    assert run.status_code == 200, run.text

    handoff = client.get(f"/api/pipeline/{opportunity_id}/e1-outputs", headers=headers)
    assert handoff.status_code == 200, handoff.text
    data = handoff.json()
    assert "Cisco" in data["vendor_list"]
    assert len(data["requirements_baseline"]) >= 1

    package = client.get(f"/api/v1/rfp/packages/{opportunity_id}", headers=headers)
    assert package.status_code == 200, package.text
    assert package.json()["step_outputs"]["e1"]["vendor_list"] == data["vendor_list"]
