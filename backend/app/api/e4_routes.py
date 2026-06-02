from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.engines.e4 import run_e4_pipeline
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from sqlalchemy.orm.attributes import flag_modified

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e4" / "output"

router = APIRouter(prefix="/e4", tags=["e4"])


@router.post('/generate')
async def generate_rfi(
    rfp_session_id: str = Form(''),
    project_name: str = Form('RFI Project'),
    db: Session = Depends(get_db),
):
    session_id: Optional[str] = rfp_session_id.strip() or None
    result = run_e4_pipeline(session_id, db)
    if session_id:
        opportunity = (
            db.query(Opportunity)
            .filter(Opportunity.opportunity_id == session_id)
            .first()
        )
        if opportunity:
            pipeline_state = (
                db.query(PipelineState)
                .filter(PipelineState.opportunity_id == opportunity.id)
                .first()
            )
            if pipeline_state:
                outputs = dict(pipeline_state.step_outputs or {})
                outputs['e4'] = {
                    'project_name': result.get('project_name', ''),
                    'total_questions': result.get('total_questions', 0),
                    'categories': result.get('categories', []),
                    'must_have_count': result.get('must_have_count', 0),
                    'nice_to_have_count': result.get('nice_to_have_count', 0),
                    'output_file': result.get('output_file', ''),
                }
                pipeline_state.step_outputs = outputs
                pipeline_state.current_step = max(pipeline_state.current_step, 11)
                opportunity.status = 'e4_complete'
                flag_modified(pipeline_state, 'step_outputs')
                db.commit()
    return result


@router.get("/download/{filename}")
def download_rfi(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path = _OUTPUT_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{safe_name}' not found.")

    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


def _get_e4_opportunity_and_pipeline(opportunity_id: str, db: Session):
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
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline state not found.")
    return opportunity, pipeline


@router.get("/{opportunity_id}/state")
def get_e4_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return E4 step outputs and opportunity info."""
    opportunity, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)
    e4_data = (pipeline.step_outputs or {}).get("e4")
    if not e4_data:
        raise HTTPException(status_code=404, detail="E4 has not been run for this opportunity.")
    return {
        "opportunity_id": opportunity_id,
        "project_name": opportunity.project_name,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "e4": e4_data,
    }


@router.post("/{opportunity_id}/checkpoint/approve")
def approve_e4_checkpoint(opportunity_id: str, db: Session = Depends(get_db)):
    """Approve the E4 checkpoint. Returns next URL (E5 design)."""
    opportunity, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=409,
            detail="E4 not yet complete. Generate the RFI questionnaire first.",
        )
    if opportunity.status == "e4_approved":
        raise HTTPException(status_code=409, detail="E4 checkpoint already approved.")

    opportunity.status = "e4_approved"
    pipeline.current_step = max(pipeline.current_step, 12)
    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "status": "e4_approved",
        "next_url": f"/e5?session_id={opportunity_id}",
        "message": "E4 approved. Proceed to E5 design generation.",
    }
