from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import E5ComponentArtifact


def read_e5_data(session_id: str, db: Session) -> dict:
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == session_id)
        .first()
    )
    if not opportunity:
        return {"components": [], "artifact": None}

    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    persisted = (pipeline.step_outputs or {}).get("e5_components") if pipeline else None
    if not persisted:
        return {"components": [], "artifact": None}

    artifact = E5ComponentArtifact.model_validate(persisted)
    return {
        "components": [
            component.model_dump(mode="json")
            for component in artifact.components
        ],
        "artifact": artifact,
    }
