import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.reviewer import run_e2_reviewer
from app.db import get_db
from app.engines.e2 import run_e2_pipeline
from app.api.pipeline_routes import get_e1_output_for_opportunity
from app.config import get_settings
from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from sqlalchemy.orm.attributes import flag_modified

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e2" / "output"

router = APIRouter(prefix="/e2", tags=["e2"])


@router.post("/analyze")
async def analyze_boq(
    rfp_session_id: str = Form(default=""),
    boq_template: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    pipeline_state = None
    e1_output = None

    if rfp_session_id.strip():
        opportunity = (
            db.query(Opportunity)
            .filter(Opportunity.opportunity_id == rfp_session_id)
            .first()
        )
        if not opportunity:
            raise HTTPException(status_code=404, detail=f"Session '{rfp_session_id}' not found.")

        documents = (
            db.query(Document)
            .filter(Document.opportunity_id == opportunity.id)
            .all()
        )

        pipeline_state = (
            db.query(PipelineState)
            .filter(PipelineState.opportunity_id == opportunity.id)
            .first()
        )
        e1_output = get_e1_output_for_opportunity(rfp_session_id.strip(), db)

        rfp_texts = [doc.text_content for doc in documents if doc.text_content]
        if not rfp_texts:
            raise HTTPException(
                status_code=400,
                detail="No RFP text found for this session. Run E1 analysis first.",
            )

        rfp_text = "\n\n".join(rfp_texts)
    else:
        rfp_text = ""

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        template_name = Path(boq_template.filename or "template.xlsx").name
        template_path = tmp_dir / template_name
        template_path.write_bytes(await boq_template.read())

        result = run_e2_pipeline(rfp_text, template_path, e1_output=e1_output)

        if pipeline_state:
            outputs = dict(pipeline_state.step_outputs or {})
            outputs['e2'] = {
                'matched_count': result.get('matched_count', 0),
                'unmatched_count': result.get('unmatched_count', 0),
                'low_confidence_count': result.get('low_confidence_count', 0),
                'subtotal': result.get('subtotal', 0),
                'discount_amount': result.get('discount_amount', 0),
                'total': result.get('total', 0),
                'currency': result.get('currency', 'USD'),
                'vendor_list': result.get('vendor_list', []),
                'requirements_baseline_count': result.get('requirements_baseline_count', 0),
                'output_file': Path(result['output_file']).name,
                'distributor_file': result.get('distributor_file') or '',
            }
            pipeline_state.step_outputs = outputs
            if (opportunity.mode or 'rfp') == 'rfi':
                pipeline_state.current_step = max(pipeline_state.current_step, 22)
                opportunity.status = 'e2_complete'
            else:
                pipeline_state.current_step = max(pipeline_state.current_step, 21)
                opportunity.status = 'e2_complete'
            # Run automated reviewer before engineer sees E2 checkpoint
            settings = get_settings()
            review_result = run_e2_reviewer(outputs['e2'], settings.anthropic_api_key)
            outputs['review_e2'] = review_result
            pipeline_state.step_outputs = outputs
            flag_modified(pipeline_state, 'step_outputs')
            db.commit()

        # Replace full path with just the filename so the caller can use the download endpoint
        result["output_file"] = Path(result["output_file"]).name
        return result
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/download/{filename}")
def download_output(filename: str):
    # Reject any path traversal attempt
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


def _get_e2_opportunity_and_pipeline(opportunity_id: str, db: Session):
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
def get_e2_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return E2 step outputs and opportunity info."""
    opportunity, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)
    e2_data = (pipeline.step_outputs or {}).get("e2")
    if not e2_data:
        raise HTTPException(status_code=404, detail="E2 has not been run for this opportunity.")
    return {
        "opportunity_id": opportunity_id,
        "project_name": opportunity.project_name,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "e2": e2_data,
    }


@router.post("/{opportunity_id}/checkpoint/approve")
def approve_e2_checkpoint(opportunity_id: str, db: Session = Depends(get_db)):
    """Approve the E2 checkpoint. Advances pipeline and returns next URL."""
    opportunity, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 21:
        raise HTTPException(
            status_code=409,
            detail="E2 not yet complete. Run E2 analysis first.",
        )
    if opportunity.status == "e2_approved":
        raise HTTPException(status_code=409, detail="E2 checkpoint already approved.")

    opportunity.status = "e2_approved"
    pipeline.current_step = max(pipeline.current_step, 22)
    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "status": "e2_approved",
        "next_url": f"/e3?session_id={opportunity_id}",
        "message": "E2 approved. Proceed to E3 proposal generation.",
    }


@router.get("/{opportunity_id}/review")
def get_e2_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the stored E2 review result."""
    _, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)
    result = (pipeline.step_outputs or {}).get("review_e2")
    if not result:
        raise HTTPException(status_code=404, detail="E2 review has not run yet.")
    return result


@router.post("/{opportunity_id}/review/rerun")
def rerun_e2_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Re-trigger the E2 reviewer without re-running the full engine."""
    from app.config import get_settings
    settings = get_settings()
    _, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)
    e2_data = (pipeline.step_outputs or {}).get("e2")
    if not e2_data:
        raise HTTPException(status_code=404, detail="E2 has not been run yet.")
    review_result = run_e2_reviewer(e2_data, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_e2": review_result}
    flag_modified(pipeline, "step_outputs")
    db.commit()
    return review_result


class E2RevisionRequest(BaseModel):
    engineer_notes: str = ""


def _get_e2_revision_count(pipeline: PipelineState) -> int:
    counts = (pipeline.step_outputs or {}).get("revision_counts", {})
    return counts.get("e2", 0)


def _increment_e2_revision_count(pipeline: PipelineState) -> int:
    outputs = dict(pipeline.step_outputs or {})
    counts = dict(outputs.get("revision_counts", {}))
    counts["e2"] = counts.get("e2", 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = outputs
    return counts["e2"]


@router.post("/{opportunity_id}/checkpoint/revise")
def revise_e2_checkpoint(
    opportunity_id: str,
    body: E2RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an E2 revision request. Max 3 revisions.
    Does not re-run the engine - engineer must re-submit via the BoM Builder.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 21:
        raise HTTPException(
            status_code=409,
            detail="E2 not yet complete. Run E2 analysis first.",
        )
    if opportunity.status == "e2_approved":
        raise HTTPException(
            status_code=409,
            detail="E2 checkpoint already approved. Revisions are no longer possible.",
        )

    current_count = _get_e2_revision_count(pipeline)
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for E2. "
                   "Edit output files manually before approving.",
        )

    new_count = _increment_e2_revision_count(pipeline)

    # Store engineer notes for audit trail
    outputs = dict(pipeline.step_outputs)
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"e2_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes
    pipeline.step_outputs = outputs

    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "message": "Revision recorded. Re-run E2 via the BoM Builder to apply changes.",
        "rerun_url": f"/e2?session_id={opportunity_id}",
    }
