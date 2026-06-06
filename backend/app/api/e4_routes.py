import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.reviewer import run_e4_reviewer
from app.config import get_settings
from app.db import get_db
from app.engines.e4 import run_e4_pipeline
from app.engines.e4.response_parser import parse_rfi_response
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import (
    E4BaselineArtifact,
    E4QuestionnaireArtifact,
    deserialize_pipeline_state_outputs,
    serialize_pipeline_state_outputs,
)
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
                outputs = deserialize_pipeline_state_outputs(pipeline_state.step_outputs).model_dump(
                    mode="json",
                    by_alias=True,
                    exclude_none=True,
                )
                outputs['e4'] = {
                    'project_name': result.get('project_name', ''),
                    'total_questions': result.get('total_questions', 0),
                    'categories': result.get('categories', []),
                    'must_have_count': result.get('must_have_count', 0),
                    'nice_to_have_count': result.get('nice_to_have_count', 0),
                    'output_file': result.get('output_file', ''),
                    'generated_from': result.get('generated_from', 'blank'),
                    'questions': result.get('questions', []),
                }
                pipeline_state.step_outputs = serialize_pipeline_state_outputs(outputs)
                pipeline_state.current_step = max(pipeline_state.current_step, 11)
                opportunity.status = 'e4_complete'
                # Run automated reviewer before engineer sees E4 checkpoint
                settings = get_settings()
                review_result = run_e4_reviewer(outputs['e4'], settings.anthropic_api_key)
                outputs['review_e4'] = review_result
                pipeline_state.step_outputs = serialize_pipeline_state_outputs(outputs)
                db.commit()
    return result


@router.post("/{opportunity_id}/responses")
async def upload_rfi_response(
    opportunity_id: str,
    response_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    opportunity, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    e4_data = outputs.e4.model_dump(mode="json") if outputs.e4 else None
    if not e4_data:
        raise HTTPException(status_code=409, detail="Generate the E4 questionnaire before uploading responses.")

    filename = Path(response_file.filename or "").name
    extension = Path(filename).suffix.lower()
    if extension not in {".xlsx", ".pdf"}:
        raise HTTPException(status_code=400, detail="RFI response must be an XLSX or PDF file.")

    temp_dir = Path(tempfile.mkdtemp())
    try:
        response_path = temp_dir / filename
        response_path.write_bytes(await response_file.read())
        try:
            artifact = parse_rfi_response(
                response_path,
                e4_data.get("questions", []),
                filename,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Unable to parse RFI response: {exc}") from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    outputs["e4_baseline"] = artifact
    pipeline.step_outputs = serialize_pipeline_state_outputs(outputs)
    db.commit()

    return E4BaselineArtifact.model_validate(outputs["e4_baseline"])


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
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    e4_data = outputs.e4.model_dump(mode="json") if outputs.e4 else None
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


@router.get("/{opportunity_id}/review")
def get_e4_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the stored E4 review result."""
    _, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    result = outputs.review_e4
    if not result:
        raise HTTPException(status_code=404, detail="E4 review has not run yet.")
    return result


@router.post("/{opportunity_id}/review/rerun")
def rerun_e4_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Re-trigger the E4 reviewer without re-running the full engine."""
    from app.config import get_settings
    settings = get_settings()
    _, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    e4_data = outputs.e4.model_dump(mode="json") if outputs.e4 else None
    if not e4_data:
        raise HTTPException(status_code=404, detail="E4 has not been run yet.")
    review_result = run_e4_reviewer(e4_data, settings.anthropic_api_key)
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    outputs["review_e4"] = review_result
    pipeline.step_outputs = serialize_pipeline_state_outputs(outputs)
    db.commit()
    return review_result


class E4RevisionRequest(BaseModel):
    engineer_notes: str = ""


def _get_e4_revision_count(pipeline: PipelineState) -> int:
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    counts = outputs.revision_counts
    return counts.get("e4", 0)


def _increment_e4_revision_count(pipeline: PipelineState) -> int:
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    counts = dict(outputs.get("revision_counts", {}))
    counts["e4"] = counts.get("e4", 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = serialize_pipeline_state_outputs(outputs)
    return counts["e4"]


@router.post("/{opportunity_id}/checkpoint/revise")
def revise_e4_checkpoint(
    opportunity_id: str,
    body: E4RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an E4 revision request. Max 3 revisions.
    Engineer must re-submit via the RFI Generator to apply changes.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=409,
            detail="E4 not yet complete. Generate the RFI questionnaire first.",
        )
    if opportunity.status == "e4_approved":
        raise HTTPException(
            status_code=409,
            detail="E4 checkpoint already approved. Revisions are no longer possible.",
        )

    current_count = _get_e4_revision_count(pipeline)
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for E4. "
                   "Edit output files manually before approving.",
        )

    new_count = _increment_e4_revision_count(pipeline)

    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"e4_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes
    pipeline.step_outputs = serialize_pipeline_state_outputs(outputs)
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "message": "Revision recorded. Re-run E4 via the RFI Generator to apply changes.",
        "rerun_url": f"/e4?session_id={opportunity_id}",
    }
