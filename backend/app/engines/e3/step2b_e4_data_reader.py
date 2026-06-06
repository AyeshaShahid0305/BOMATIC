from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import deserialize_pipeline_state_outputs


def read_e4_data(session_id: str, db: Session) -> dict:
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == session_id)
        .first()
    )
    if not opportunity:
        return {"requirements": [], "gaps": [], "artifact": None}

    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs if pipeline else None)
    artifact = outputs.e4_baseline
    if not artifact:
        return {"requirements": [], "gaps": [], "artifact": None}

    requirements = [
        {
            "text": f"{requirement.question}: {requirement.answer}",
            "category": requirement.category,
            "source": "e4_rfi_response",
            "question_id": requirement.question_id,
            "question": requirement.question,
            "compliance_status": "confirmed",
        }
        for requirement in artifact.requirements
        if requirement.status == "answered"
    ]
    gaps = [
        requirement.model_dump(mode="json")
        for requirement in artifact.requirements
        if requirement.status in {"missing", "insufficient"}
    ]
    return {"requirements": requirements, "gaps": gaps, "artifact": artifact}
