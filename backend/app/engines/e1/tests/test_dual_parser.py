from app.engines.e1 import step3_requirements_extractor as extractor
from app.engines.e1.step3_requirements_extractor import (
    compare_and_merge,
    dual_parse_rfp,
    python_parser,
)


SAMPLE_TEXT = (
    "The solution shall support 500 concurrent users. "
    "Redundant power supplies are required. "
    "The system should support IPv6. "
    "Vendor may provide optional training. "
    "The firewall must integrate with existing Cisco DNA Center."
)


def test_python_parser_finds_mandatory_requirement():
    results = python_parser(SAMPLE_TEXT)
    assert any(req.classification == "mandatory" for req in results)


def test_python_parser_finds_optional_requirement():
    results = python_parser(SAMPLE_TEXT)
    assert any(req.classification == "optional" for req in results)


def test_compare_and_merge_returns_expected_keys():
    python_results = python_parser(SAMPLE_TEXT)
    merged = compare_and_merge(python_results, python_results)
    assert set(merged.keys()) == {"confirmed", "python_only", "ai_only", "conflicts"}


def test_compare_and_merge_identical_inputs_are_confirmed():
    python_results = python_parser(SAMPLE_TEXT)
    merged = compare_and_merge(python_results, python_results)
    assert len(merged["confirmed"]) == len(python_results)
    assert merged["python_only"] == []
    assert merged["ai_only"] == []
    assert merged["conflicts"] == []


def test_dual_parse_rfp_returns_summary(monkeypatch):
    python_results = python_parser(SAMPLE_TEXT)
    monkeypatch.setattr(extractor, "ai_parser", lambda text, source_file="ai_parser": python_results)

    result = dual_parse_rfp({"sample.txt": SAMPLE_TEXT}, "OPP-001")

    assert "summary" in result
    assert "confirmed_count" in result["summary"]


def test_dual_parse_rfp_total_found_matches_component_counts(monkeypatch):
    python_results = python_parser(SAMPLE_TEXT)
    monkeypatch.setattr(extractor, "ai_parser", lambda text, source_file="ai_parser": python_results)

    result = dual_parse_rfp({"sample.txt": SAMPLE_TEXT}, "OPP-001")

    expected_total = (
        result["summary"]["confirmed_count"]
        + result["summary"]["python_only_count"]
        + result["summary"]["ai_only_count"]
    )
    assert result["total_found"] == expected_total
