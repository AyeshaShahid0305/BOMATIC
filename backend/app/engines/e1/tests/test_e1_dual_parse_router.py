import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.e1_router import router
from app.db import get_db
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState


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
    def __init__(self, opportunity=None, pipeline=None):
        self.opportunity = opportunity
        self.pipeline = pipeline

    def query(self, entity):
        return FakeQuery(self, entity)


def _make_client(fake_db: FakeDB):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake_db
    return TestClient(app)


def test_dual_parse_returns_404_before_pipeline_runs():
    opportunity = Opportunity(
        id=uuid.uuid4(),
        opportunity_id="OPP-DUAL-000",
        project_name="Dual Parse Test",
    )
    pipeline = PipelineState(
        opportunity_id=opportunity.id,
        current_step=0,
        step_outputs={},
    )
    fake_db = FakeDB(opportunity=opportunity, pipeline=pipeline)

    with _make_client(fake_db) as client:
        response = client.get("/e1/OPP-DUAL-000/dual-parse")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_dual_parse_returns_404_when_key_missing():
    opportunity = Opportunity(
        id=uuid.uuid4(),
        opportunity_id="OPP-DUAL-001",
        project_name="Dual Parse Test",
    )
    pipeline = PipelineState(
        opportunity_id=opportunity.id,
        current_step=4,
        step_outputs={},
    )
    fake_db = FakeDB(opportunity=opportunity, pipeline=pipeline)

    with _make_client(fake_db) as client:
        response = client.get("/e1/OPP-DUAL-001/dual-parse")

    assert response.status_code == 404


def test_dual_parse_returns_200_with_correct_keys():
    opportunity_id = "OPP-DUAL-002"
    opportunity = Opportunity(
        id=uuid.uuid4(),
        opportunity_id=opportunity_id,
        project_name="Dual Parse Test",
    )
    pipeline = PipelineState(
        opportunity_id=opportunity.id,
        current_step=4,
        step_outputs={
            "dual_parse": {
                "confirmed_count": 5,
                "python_only_count": 2,
                "ai_only_count": 1,
                "conflict_count": 0,
                "total_found": 8,
                "needs_review_count": 1,
                "ai_only": [],
                "conflicts": [],
            }
        },
    )
    fake_db = FakeDB(opportunity=opportunity, pipeline=pipeline)

    with _make_client(fake_db) as client:
        response = client.get(f"/e1/{opportunity_id}/dual-parse")

    assert response.status_code == 200
    payload = response.json()
    assert payload["opportunity_id"] == opportunity_id
    assert "dual_parse" in payload
    assert payload["dual_parse"]["confirmed_count"] == 5
    assert payload["dual_parse"]["total_found"] == 8


def test_dual_parse_returns_404_for_unknown_opportunity():
    fake_db = FakeDB(opportunity=None, pipeline=None)

    with _make_client(fake_db) as client:
        response = client.get("/e1/nonexistent-opportunity-id/dual-parse")

    assert response.status_code == 404
