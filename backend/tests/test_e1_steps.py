import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.engines.e1.step2_missing_docs import detect_missing_documents
from app.engines.e1.step4_legal_trap_flagger import detect_legal_traps
from app.engines.e1.step8_sector_detector import detect_sector
from app.engines.e1.step9_framework_selector import select_frameworks
from app.engines.e1.step11_tp_linker import link_tp_sections
from app.engines.e1.step12_xlsx_writer import write_compliance_matrix_xlsx


# ---------------------------------------------------------------------------
# Step 2 — detect_missing_documents
# ---------------------------------------------------------------------------

def test_step2_detects_missing_annex():
    classified_files = [{"filename": "rfp_main.pdf"}]
    texts = {"rfp_main.pdf": "As per Annex A, the vendor shall comply with all technical specifications."}
    result = detect_missing_documents(classified_files, texts)
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# Step 4 — detect_legal_traps
# ---------------------------------------------------------------------------

def test_step4_detects_bid_bond_as_critical_or_high():
    texts = {"rfp.pdf": "A bid bond is required from all bidders prior to submission."}
    result = detect_legal_traps(texts)
    assert len(result) >= 1
    assert any(f.severity in {"critical", "high"} for f in result)


# ---------------------------------------------------------------------------
# Step 8 — detect_sector
# ---------------------------------------------------------------------------

def test_step8_known_client_not_general():
    result = detect_sector("STC Solutions", {})
    assert result["sector"] != "general"


def test_step8_unknown_client_is_general():
    result = detect_sector("unknown_client_xyz", {})
    assert result["sector"] == "general"
    assert result["confidence"] == 0.3


# ---------------------------------------------------------------------------
# Step 9 — select_frameworks
# ---------------------------------------------------------------------------

def test_step9_telecom_returns_non_empty_string_list():
    result = select_frameworks("telecom", [])
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(fw, str) for fw in result)


def test_step9_general_returns_list():
    result = select_frameworks("general", [])
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Step 11 — link_tp_sections
# ---------------------------------------------------------------------------

def test_step11_firewall_requirement_maps_to_network_section():
    rows = [{
        "req_id": "R-001",
        "req_text": "The vendor shall provide firewall and network segmentation.",
        "classification": "mandatory",
        "control_name": "",
        "gap_type": "none",
    }]
    result = link_tp_sections(rows)
    assert result[0]["tp_section"] == "§6 Network Security Architecture"


def test_step11_mandatory_row_always_receives_tp_section():
    # ValueError guard in link_tp_sections is a defensive invariant — the function
    # always assigns tp_section before checking it, so no row can leave it empty.
    rows = [{
        "req_id": "R-002",
        "req_text": "The vendor shall provide incident response and disaster recovery procedures.",
        "classification": "mandatory",
        "control_name": "",
        "gap_type": "none",
    }]
    result = link_tp_sections(rows)
    assert result[0]["tp_section"]  # non-empty, must not raise


# ---------------------------------------------------------------------------
# Step 12 — write_compliance_matrix_xlsx
# ---------------------------------------------------------------------------

def test_step12_writes_xlsx_file(tmp_path):
    matrix_rows = [{
        "req_id": "R-001",
        "req_text": "The vendor shall provide a firewall.",
        "classification": "mandatory",
        "framework": "NCA_ECC2",
        "control_id": "ECC-1-1",
        "control_name": "Network Security",
        "status": "Compliant",
        "tp_section": "§6 Network Security Architecture",
        "notes": "",
        "gap_type": "none",
    }]
    gaps = {"coverage_gaps": [], "orphan_requirements": []}
    stats = {
        "total_reqs": 1, "compliant": 1, "partial": 0,
        "non_compliant": 0, "alternative": 0, "orphans": 0, "coverage_gaps": 0,
    }
    out = write_compliance_matrix_xlsx(matrix_rows, gaps, stats, "TEST-001", tmp_path)
    assert out.exists()
    assert out.suffix == ".xlsx"
