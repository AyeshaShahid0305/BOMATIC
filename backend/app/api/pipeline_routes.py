from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import E1Output

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def get_e1_output_for_opportunity(opportunity_id: str, db: Session) -> E1Output:
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == opportunity_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' not found.")

    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    e1_output = (pipeline.step_outputs or {}).get("e1") if pipeline else None
    if not e1_output:
        raise HTTPException(status_code=404, detail="E1 outputs are not available yet.")

    try:
        return E1Output.model_validate(e1_output)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@router.get("/{opportunity_id}/e1-outputs", response_model=E1Output)
def get_e1_outputs(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the validated E1 handoff payload for downstream engines."""
    return get_e1_output_for_opportunity(opportunity_id, db)
