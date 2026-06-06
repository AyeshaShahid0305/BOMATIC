import sys
import uuid
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import openpyxl
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.e4_routes import router
from app.db import get_db
from app.engines.e4.response_parser import parse_rfi_response
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import E4BaselineArtifact


QUESTIONS = [
    {
        "id": "RFI-001",
        "category": "Network",
        "question": "Describe the current topology.",
        "priority": "must_have",
        "expected_answer_type": "text",
    },
    {
        "id": "RFI-002",
        "category": "Scale",
        "question": "How many users are required?",
        "priority": "must_have",
        "expected_answer_type": "number",
    },
]


def _response_workbook(second_answer=""):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "RFI Questionnaire"
    worksheet.append(
        ["RFI ID", "Category", "Priority", "Question", "Rationale", "Answer Type", "Response"]
    )
    worksheet.append(
        ["RFI-001", "Network", "must_have", QUESTIONS[0]["question"], "", "text", "Core and access design attached."]
    )
    worksheet.append(
        ["RFI-002", "Scale", "must_have", QUESTIONS[1]["question"], "", "number", second_answer]
    )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class FakeQuery:
    def __init__(self, db, entity):
        self.db = db
        self.entity = entity

    def filter(self, *_conditions):
        return self

    def first(self):
        if self.entity is Opportunity:
            return self.db.opportunity
        if self.entity is PipelineState:
            return self.db.pipeline
        return None


class FakeDB:
    def __init__(self):
        self.opportunity = Opportunity(
            id=uuid.uuid4(),
            opportunity_id="OPP-E4-RESPONSE",
            project_name="RFI Response Test",
        )
        self.pipeline = PipelineState(
            opportunity_id=self.opportunity.id,
            step_outputs={"e4": {"questions": QUESTIONS}},
        )
        self.committed = False

    def query(self, entity):
        return FakeQuery(self, entity)

    def commit(self):
        self.committed = True


def test_gap_detection_flags_missing_answer(tmp_path):
    response_path = tmp_path / "responses.xlsx"
    response_path.write_bytes(_response_workbook(second_answer=""))

    artifact = parse_rfi_response(response_path, QUESTIONS, response_path.name)

    assert artifact.gap_count == 1
    assert artifact.requirements[1].status == "missing"
    assert artifact.requirements[1].gap_reason


def test_gap_detection_flags_insufficient_answer(tmp_path):
    response_path = tmp_path / "responses.xlsx"
    response_path.write_bytes(_response_workbook(second_answer="TBD"))

    artifact = parse_rfi_response(response_path, QUESTIONS, response_path.name)

    assert artifact.gap_count == 1
    assert artifact.requirements[1].status == "insufficient"


def test_response_upload_persists_loadable_baseline_artifact():
    fake_db = FakeDB()
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: fake_db

    with TestClient(app) as client:
        response = client.post(
            "/api/e4/OPP-E4-RESPONSE/responses",
            files={
                "response_file": (
                    "responses.xlsx",
                    _response_workbook(second_answer="250"),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 200, response.text
    assert fake_db.committed is True
    persisted = fake_db.pipeline.step_outputs["e4_baseline"]
    artifact = E4BaselineArtifact.model_validate(persisted)
    assert artifact.source_filename == "responses.xlsx"
    assert artifact.answered_count == 2
    assert len(artifact.requirements) == 2
