import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.e3_routes import router
from app.db import get_db
from app.engines.e3.step5_assembler import ProposalIncompleteError
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
    def __init__(self):
        self.opportunity = Opportunity(
            id=uuid.uuid4(),
            opportunity_id="OPP-E3-PLACEHOLDER",
        )
        self.pipeline = PipelineState(
            opportunity_id=self.opportunity.id,
            step_outputs={},
        )

    def query(self, entity):
        return FakeQuery(self, entity)


def test_incomplete_proposal_returns_structured_422(monkeypatch):
    fake_db = FakeDB()
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: fake_db
    monkeypatch.setattr(
        "app.api.e3_routes.run_e3_pipeline",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ProposalIncompleteError([{"id": 0, "title": "Cover Page"}])
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/e3/generate",
            data={"rfp_session_id": "OPP-E3-PLACEHOLDER"},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["incomplete_sections"] == [
        {"id": 0, "title": "Cover Page"}
    ]
