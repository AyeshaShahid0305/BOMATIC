import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from app.config import get_settings
from app.db import get_db
from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.models.user import User
from app.routers.rfp import router


class FakeQuery:
    def __init__(self, db, entities):
        self.db = db
        self.entities = entities
        self.filters = []

    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self

    def join(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        entity = self.entities[0]
        if entity is User:
            requested_id = str(self.filters[-1].right.value)
            return self.db.users.get(requested_id)
        if entity is Opportunity:
            return self.db.opportunity
        if entity is PipelineState:
            return self.db.pipeline
        return None

    def all(self):
        if self.entities[0] is Document:
            return []
        if self.entities == (Opportunity, PipelineState):
            requested_owner = str(self.filters[-1].right.value)
            if self.db.opportunity.user_id == requested_owner:
                return [(self.db.opportunity, self.db.pipeline)]
            return []
        return []


class FakeDB:
    def __init__(self, users, opportunity, pipeline):
        self.users = {str(user.id): user for user in users}
        self.opportunity = opportunity
        self.pipeline = pipeline

    def query(self, *entities):
        return FakeQuery(self, entities)


@pytest.fixture
def authorization_client():
    owner = User(
        id=uuid.uuid4(),
        email="owner@example.com",
        hashed_password="unused",
        full_name="Owner",
        is_active=True,
    )
    other_user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        hashed_password="unused",
        full_name="Other",
        is_active=True,
    )
    opportunity = Opportunity(
        id=uuid.uuid4(),
        opportunity_id="OPP-AUTH-TEST",
        project_name="Authorization Test",
        client_name="Test Client",
        user_id=str(owner.id),
        created_at=datetime.now(timezone.utc),
    )
    pipeline = PipelineState(
        opportunity_id=opportunity.id,
        current_step=0,
        step_outputs={},
    )
    fake_db = FakeDB([owner, other_user], opportunity, pipeline)

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = lambda: fake_db

    settings = get_settings()

    def token_for(user):
        return jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    with TestClient(test_app) as client:
        yield client, token_for(owner), token_for(other_user)


def test_unauthenticated_opportunity_read_returns_401(authorization_client):
    client, _, _ = authorization_client

    response = client.get("/api/v1/rfp/packages/OPP-AUTH-TEST")

    assert response.status_code == 401


def test_wrong_user_opportunity_read_returns_403(authorization_client):
    client, _, other_token = authorization_client

    response = client.get(
        "/api/v1/rfp/packages/OPP-AUTH-TEST",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 403


def test_owner_opportunity_read_returns_200(authorization_client):
    client, owner_token, _ = authorization_client

    response = client.get(
        "/api/v1/rfp/packages/OPP-AUTH-TEST",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    assert response.json()["opportunity_id"] == "OPP-AUTH-TEST"
