from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.engines.e5 import run_e5_pipeline
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from sqlalchemy.orm.attributes import flag_modified

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e5" / "output"

router = APIRouter(prefix="/e5", tags=["e5"])


@router.post("/generate")
async def generate_design(
    rfp_session_id: str = Form(...),
    db: Session = Depends(get_db),
):
    session_id = rfp_session_id.strip()
    result = run_e5_pipeline(session_id, db)

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
            outputs['e5'] = {
                'project_name': result.get('project_name', ''),
                'total_sections': result.get('total_sections', 0),
                'output_file': result.get('output_file', ''),
            }
            pipeline_state.step_outputs = outputs
            pipeline_state.current_step = max(pipeline_state.current_step, 21)
            opportunity.status = 'e5_complete'
            flag_modified(pipeline_state, 'step_outputs')
            db.commit()

    return result


@router.get("/download/{filename}")
def download_design(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path = _OUTPUT_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{safe_name}' not found.")

    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


def _get_e5_opportunity_and_pipeline(opportunity_id: str, db: Session):
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
def get_e5_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return E5 step outputs and opportunity info."""
    opportunity, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)
    e5_data = (pipeline.step_outputs or {}).get("e5")
    if not e5_data:
        raise HTTPException(status_code=404, detail="E5 has not been run for this opportunity.")
    return {
        "opportunity_id": opportunity_id,
        "project_name": opportunity.project_name,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "e5": e5_data,
    }


@router.post("/{opportunity_id}/checkpoint/approve")
def approve_e5_checkpoint(opportunity_id: str, db: Session = Depends(get_db)):
    """Approve the E5 checkpoint. Returns next URL (E2 BoM for RFI mode)."""
    opportunity, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 21:
        raise HTTPException(
            status_code=409,
            detail="E5 not yet complete. Generate the design document first.",
        )
    if opportunity.status == "e5_approved":
        raise HTTPException(status_code=409, detail="E5 checkpoint already approved.")

    opportunity.status = "e5_approved"
    pipeline.current_step = max(pipeline.current_step, 22)
    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "status": "e5_approved",
        "next_url": f"/e2?session_id={opportunity_id}",
        "message": "E5 approved. Proceed to E2 BoM generation.",
    }
