import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engines.e3.pipeline import run_e3_pipeline
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import (
    E4BaselineArtifact,
    E4BaselineRequirement,
    E5Component,
    E5ComponentArtifact,
)


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
    def __init__(self, step_outputs):
        self.opportunity = Opportunity(
            id=uuid.uuid4(),
            opportunity_id="OPP-E3-CONTEXT",
            project_name="Context Test",
        )
        self.pipeline = PipelineState(
            opportunity_id=self.opportunity.id,
            step_outputs=step_outputs,
        )

    def query(self, entity):
        return FakeQuery(self, entity)


def test_e3_pipeline_with_e4_e5_artifacts_produces_richer_output(tmp_path, monkeypatch):
    e4_artifact = E4BaselineArtifact(
        source_filename="responses.xlsx",
        requirements=[
            E4BaselineRequirement(
                question_id="RFI-001",
                category="Scale",
                question="How many users are required?",
                answer="500 users",
                status="answered",
            )
        ],
        answered_count=1,
        gap_count=0,
    )
    e5_artifact = E5ComponentArtifact(
        components=[
            E5Component(
                description="48-port PoE+ access switch",
                quantity=10,
                category="network",
            )
        ]
    )
    captured_documents = []

    monkeypatch.setattr(
        "app.engines.e3.pipeline.read_e1_data",
        lambda _session_id, _db: {
            "project_name": "Context Test",
            "requirements": [],
            "legal_traps": [],
            "missing_documents": [],
            "rfp_text": "",
        },
    )

    def narratives(e1_data, e2_data, sections, _tier):
        requirement_text = " | ".join(
            requirement["text"] for requirement in e1_data["requirements"]
        )
        component_text = " | ".join(
            component["description"]
            for component in e2_data["design_components"]
        )
        return {
            section.id: (
                f"Requirements: {requirement_text}; Components: {component_text}"
                if section.title == "Proposed Solution"
                else "Completed section content."
            )
            for section in sections
        }

    monkeypatch.setattr("app.engines.e3.pipeline.generate_narratives", narratives)

    def write_document(sections, _project_name, _tier):
        captured_documents.append(
            "\n".join(section["content"] for section in sections)
        )
        path = tmp_path / f"proposal-{len(captured_documents)}.docx"
        path.write_bytes(b"test")
        return path

    monkeypatch.setattr("app.engines.e3.pipeline.write_proposal", write_document)
    monkeypatch.setattr(
        "app.engines.e3.pipeline.convert_docx_to_pdf",
        lambda *_args: None,
    )

    without_artifacts = run_e3_pipeline(
        "OPP-E3-CONTEXT",
        FakeDB({}),
    )
    with_artifacts = run_e3_pipeline(
        "OPP-E3-CONTEXT",
        FakeDB(
            {
                "e4_baseline": e4_artifact.model_dump(mode="json"),
                "e5_components": e5_artifact.model_dump(mode="json"),
            }
        ),
    )

    assert "500 users" not in captured_documents[0]
    assert "48-port PoE+ access switch" not in captured_documents[0]
    assert "500 users" in captured_documents[1]
    assert "48-port PoE+ access switch" in captured_documents[1]
    assert with_artifacts["e4_requirement_count"] > without_artifacts["e4_requirement_count"]
    assert with_artifacts["e5_component_count"] > without_artifacts["e5_component_count"]
