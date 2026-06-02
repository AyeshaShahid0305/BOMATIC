from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.reviewer import run_e5_reviewer
from app.config import get_settings
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
            # Run automated reviewer before engineer sees E5 checkpoint
            settings = get_settings()
            review_result = run_e5_reviewer(outputs['e5'], settings.anthropic_api_key)
            outputs['review_e5'] = review_result
            pipeline_state.step_outputs = outputs
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


@router.get("/{opportunity_id}/review")
def get_e5_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the stored E5 review result."""
    _, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)
    result = (pipeline.step_outputs or {}).get("review_e5")
    if not result:
        raise HTTPException(status_code=404, detail="E5 review has not run yet.")
    return result


@router.post("/{opportunity_id}/review/rerun")
def rerun_e5_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Re-trigger the E5 reviewer without re-running the full engine."""
    from app.config import get_settings
    settings = get_settings()
    _, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)
    e5_data = (pipeline.step_outputs or {}).get("e5")
    if not e5_data:
        raise HTTPException(status_code=404, detail="E5 has not been run yet.")
    review_result = run_e5_reviewer(e5_data, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_e5": review_result}
    flag_modified(pipeline, "step_outputs")
    db.commit()
    return review_result


class E5RevisionRequest(BaseModel):
    engineer_notes: str = ""


def _get_e5_revision_count(pipeline: PipelineState) -> int:
    counts = (pipeline.step_outputs or {}).get("revision_counts", {})
    return counts.get("e5", 0)


def _increment_e5_revision_count(pipeline: PipelineState) -> int:
    outputs = dict(pipeline.step_outputs or {})
    counts = dict(outputs.get("revision_counts", {}))
    counts["e5"] = counts.get("e5", 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = outputs
    return counts["e5"]


@router.post("/{opportunity_id}/checkpoint/revise")
def revise_e5_checkpoint(
    opportunity_id: str,
    body: E5RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an E5 revision request. Max 3 revisions.
    Engineer must re-submit via the Design Generator to apply changes.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 21:
        raise HTTPException(
            status_code=409,
            detail="E5 not yet complete. Generate the design document first.",
        )
    if opportunity.status == "e5_approved":
        raise HTTPException(
            status_code=409,
            detail="E5 checkpoint already approved. Revisions are no longer possible.",
        )

    current_count = _get_e5_revision_count(pipeline)
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for E5. "
                   "Edit output files manually before approving.",
        )

    new_count = _increment_e5_revision_count(pipeline)

    outputs = dict(pipeline.step_outputs)
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"e5_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes
    pipeline.step_outputs = outputs

    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "message": "Revision recorded. Re-run E5 via the Design Generator to apply changes.",
        "rerun_url": f"/e5?session_id={opportunity_id}",
    }
