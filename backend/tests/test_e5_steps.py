import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import app.engines.e5.step4_docx_writer as docx_mod
from app.engines.e5.models import DesignDocument, DesignSection
from app.engines.e5.step1_context_reader import read_context
from app.engines.e5.step2_hld_generator import generate_hld
from app.engines.e5.step3_lld_generator import generate_lld
from app.engines.e5.step4_docx_writer import write_design_document


# ---------------------------------------------------------------------------
# read_context
# ---------------------------------------------------------------------------

def test_read_context_none_session_returns_blank_dict():
    result = read_context(None, db=None)
    assert isinstance(result, dict)
    assert "has_e1_data" in result
    assert "project_name" in result
    assert "rfp_text" in result
    assert "matched_items" in result
    assert "total_price" in result


def test_read_context_none_session_has_e1_data_false():
    result = read_context(None, db=None)
    assert result["has_e1_data"] is False


# ---------------------------------------------------------------------------
# generate_hld
# ---------------------------------------------------------------------------

def test_generate_hld_fallback_returns_6_sections(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = generate_hld({})
    assert isinstance(result, list)
    assert len(result) == 6


def test_generate_hld_fallback_all_hld_level_with_content(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = generate_hld({})
    assert all(isinstance(s, DesignSection) for s in result)
    assert all(s.level == "HLD" for s in result)
    assert all(s.content for s in result)


# ---------------------------------------------------------------------------
# generate_lld
# ---------------------------------------------------------------------------

def test_generate_lld_fallback_returns_6_sections(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = generate_lld({}, hld_sections=[])
    assert isinstance(result, list)
    assert len(result) == 6


def test_generate_lld_fallback_all_lld_level_with_content(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = generate_lld({}, hld_sections=[])
    assert all(isinstance(s, DesignSection) for s in result)
    assert all(s.level == "LLD" for s in result)
    assert all(s.content for s in result)


# ---------------------------------------------------------------------------
# write_design_document
# ---------------------------------------------------------------------------

def test_write_design_document_creates_docx(tmp_path, monkeypatch):
    monkeypatch.setattr(docx_mod, "_OUTPUT_DIR", tmp_path)

    doc = DesignDocument(
        project_name="Test",
        hld_sections=[
            DesignSection(id="HLD-001", title="Executive Overview", content="Overview content.", level="HLD", order=1),
        ],
        lld_sections=[
            DesignSection(id="LLD-001", title="IP Address Scheme", content="IP scheme content.", level="LLD", order=1),
        ],
    )

    out = write_design_document(doc)

    assert out.exists()
    assert out.suffix == ".docx"
