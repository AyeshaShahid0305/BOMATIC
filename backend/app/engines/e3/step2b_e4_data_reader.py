from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import E4BaselineArtifact


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
    persisted = (pipeline.step_outputs or {}).get("e4_baseline") if pipeline else None
    if not persisted:
        return {"requirements": [], "gaps": [], "artifact": None}

    artifact = E4BaselineArtifact.model_validate(persisted)
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
