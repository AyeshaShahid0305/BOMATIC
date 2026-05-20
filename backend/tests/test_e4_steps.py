import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import app.engines.e4.step4_xlsx_writer as xlsx_mod
from app.engines.e4.models import RFIQuestion, RFIQuestionnaire
from app.engines.e4.step1_context_reader import read_context
from app.engines.e4.step2_question_generator import generate_questions
from app.engines.e4.step3_assembler import assemble_questionnaire
from app.engines.e4.step4_xlsx_writer import write_questionnaire


# ---------------------------------------------------------------------------
# read_context
# ---------------------------------------------------------------------------

def test_read_context_none_session_returns_blank_dict():
    result = read_context(None, db=None)
    assert isinstance(result, dict)
    assert "has_e1_data" in result
    assert "project_name" in result
    assert "rfp_text" in result


def test_read_context_none_session_has_e1_data_false():
    result = read_context(None, db=None)
    assert result["has_e1_data"] is False


# ---------------------------------------------------------------------------
# generate_questions
# ---------------------------------------------------------------------------

def test_generate_questions_fallback_returns_5_questions(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = generate_questions({})
    assert isinstance(result, list)
    assert len(result) == 5


def test_generate_questions_fallback_all_fields_non_empty(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = generate_questions({})
    assert all(isinstance(q, RFIQuestion) for q in result)
    assert all(q.question for q in result)
    assert all(q.category for q in result)


# ---------------------------------------------------------------------------
# assemble_questionnaire
# ---------------------------------------------------------------------------

def test_assemble_questionnaire_structure():
    questions = [
        RFIQuestion(id="RFI-001", category="Network",    question="Q1?", rationale="R1", priority="must_have",    expected_answer_type="text"),
        RFIQuestion(id="RFI-002", category="Security",   question="Q2?", rationale="R2", priority="nice_to_have", expected_answer_type="yes_no"),
        RFIQuestion(id="RFI-003", category="Commercial", question="Q3?", rationale="R3", priority="must_have",    expected_answer_type="number"),
    ]
    context = {"project_name": "Test Project", "has_e1_data": False}

    result = assemble_questionnaire(questions, context)

    assert isinstance(result, RFIQuestionnaire)
    assert result.total_questions == 3
    assert len(result.categories) > 0
    assert result.generated_from == "blank"


def test_assemble_questionnaire_must_have_sorted_before_nice_to_have():
    questions = [
        RFIQuestion(id="RFI-001", category="Network",  question="Q1?", rationale="R1", priority="nice_to_have", expected_answer_type="text"),
        RFIQuestion(id="RFI-002", category="Security", question="Q2?", rationale="R2", priority="must_have",    expected_answer_type="text"),
    ]
    context = {"project_name": "Test", "has_e1_data": False}

    result = assemble_questionnaire(questions, context)

    assert result.questions[0].priority == "must_have"


# ---------------------------------------------------------------------------
# write_questionnaire
# ---------------------------------------------------------------------------

def test_write_questionnaire_creates_xlsx(tmp_path, monkeypatch):
    monkeypatch.setattr(xlsx_mod, "_OUTPUT_DIR", tmp_path)

    questionnaire = RFIQuestionnaire(
        project_name="Test",
        generated_from="blank",
        questions=[
            RFIQuestion(
                id="RFI-001",
                category="Network",
                question="Describe your network topology.",
                rationale="Required for design.",
                priority="must_have",
                expected_answer_type="attachment",
            )
        ],
        total_questions=1,
        categories=["Network"],
    )

    out = write_questionnaire(questionnaire)

    assert Path(out).exists()
    assert Path(out).suffix == ".xlsx"
