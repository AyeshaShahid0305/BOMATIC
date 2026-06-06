from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import deserialize_pipeline_state_outputs


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
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs if pipeline else None)
    artifact = outputs.e5_components
    if not artifact:
        return {"components": [], "artifact": None}
    return {
        "components": [
            component.model_dump(mode="json")
            for component in artifact.components
        ],
        "artifact": artifact,
    }
