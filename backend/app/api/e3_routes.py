import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.reviewer import run_e3_reviewer
from app.config import get_settings
from app.db import get_db
from app.engines.e2.step1_rfp_extractor import extract_rfp_requirements
from app.engines.e2.step3_catalog_matcher import match_catalog
from app.engines.e2.step4_gap_analyzer import analyze_gaps
from app.engines.e3 import run_e3_pipeline
from app.engines.e3.step5_assembler import ProposalIncompleteError
from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import (
    E2PricingArtifact,
    E3ProposalArtifact,
    deserialize_pipeline_state_outputs,
    serialize_pipeline_state_outputs,
)

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e3" / "output"

router = APIRouter(prefix="/e3", tags=["e3"])


def _load_pricing_artifact(data: dict) -> E2PricingArtifact:
    try:
        return E2PricingArtifact.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=409,
            detail="Persisted E2 pricing artifact is invalid. Re-run E2 analysis.",
        ) from exc


@router.post("/generate")
async def generate_proposal(
    rfp_session_id: str = Form(...),
    gbb_tier: str = Form("better"),
    allow_placeholders: bool = Form(False),
    boq_template: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == rfp_session_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail=f"Session '{rfp_session_id}' not found.")

    pipeline_state = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    outputs = deserialize_pipeline_state_outputs(
        pipeline_state.step_outputs if pipeline_state else None
    )
    persisted_e2 = outputs.e2.model_dump(mode="json") if outputs.e2 else None
    pricing_summary = None

    if persisted_e2:
        pricing_summary = _load_pricing_artifact(persisted_e2)
    elif boq_template is not None:
        documents = (
            db.query(Document)
            .filter(Document.opportunity_id == opportunity.id)
            .all()
        )
        rfp_texts = [doc.text_content for doc in documents if doc.text_content]
        if not rfp_texts:
            raise HTTPException(
                status_code=400,
                detail="No RFP text found for this session. Run E1 analysis first.",
            )
        rfp_text = "\n\n".join(rfp_texts)

        tmp_dir = Path(tempfile.mkdtemp())
        try:
            template_name = Path(boq_template.filename or "template.xlsx").name
            template_path = tmp_dir / template_name
            template_path.write_bytes(await boq_template.read())

            rfp_items = extract_rfp_requirements(rfp_text)
            matches = match_catalog(rfp_items)
            pricing_summary = E2PricingArtifact.from_pricing_summary(analyze_gaps(matches))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    try:
        result = run_e3_pipeline(
            rfp_session_id,
            db,
            gbb_tier,
            pricing_summary,
            allow_placeholders=allow_placeholders,
        )
        if pipeline_state:
            outputs = deserialize_pipeline_state_outputs(pipeline_state.step_outputs).model_dump(
                mode="json",
                by_alias=True,
                exclude_none=True,
            )
            outputs['e3'] = {
                'project_name': result.get('project_name', ''),
                'section_count': result.get('section_count', 0),
                'output_file': result.get('output_file', ''),
                'pdf_file': result.get('pdf_file') or '',
                'gbb_tier': result.get('gbb_tier', gbb_tier),
                'gbb_multiplier': result.get('gbb_multiplier', 1.0),
                'total_price': result.get('total_price', 0.0),
                'ai_generated_count': result.get('ai_generated_count', 0),
                'e4_requirement_count': result.get('e4_requirement_count', 0),
                'e4_gap_count': result.get('e4_gap_count', 0),
                'e5_component_count': result.get('e5_component_count', 0),
            }
            pipeline_state.step_outputs = serialize_pipeline_state_outputs(outputs)
            pipeline_state.current_step = max(pipeline_state.current_step, 23)
            opportunity.status = 'e3_complete'
            # Run automated reviewer before engineer sees E3 checkpoint
            settings = get_settings()
            review_result = run_e3_reviewer(outputs['e3'], settings.anthropic_api_key)
            outputs['review_e3'] = review_result
            pipeline_state.step_outputs = serialize_pipeline_state_outputs(outputs)
            db.commit()
        return result
    except ProposalIncompleteError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Proposal generation blocked because required sections are incomplete.",
                "incomplete_sections": exc.incomplete_sections,
                "hint": "Complete the listed sections or set allow_placeholders=true for dev/demo use.",
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/download/{filename}")
def download_proposal(filename: str):
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


def _get_e3_opportunity_and_pipeline(opportunity_id: str, db: Session):
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
def get_e3_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return E3 step outputs and opportunity info."""
    opportunity, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    e3_data = outputs.e3.model_dump(mode="json") if outputs.e3 else None
    if not e3_data:
        raise HTTPException(status_code=404, detail="E3 has not been run for this opportunity.")
    return {
        "opportunity_id": opportunity_id,
        "project_name": opportunity.project_name,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "e3": e3_data,
    }


@router.post("/{opportunity_id}/checkpoint/approve")
def approve_e3_checkpoint(opportunity_id: str, db: Session = Depends(get_db)):
    """Approve the E3 checkpoint. Marks the pipeline complete."""
    opportunity, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 23:
        raise HTTPException(
            status_code=409,
            detail="E3 not yet complete. Generate the proposal first.",
        )
    if opportunity.status == "complete":
        raise HTTPException(status_code=409, detail="E3 checkpoint already approved.")

    opportunity.status = "complete"
    pipeline.current_step = max(pipeline.current_step, 24)
    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "status": "complete",
        "next_url": f"/opportunities",
        "message": "Proposal approved. Opportunity is complete.",
    }


@router.get("/{opportunity_id}/review")
def get_e3_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the stored E3 review result."""
    _, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    result = outputs.review_e3
    if not result:
        raise HTTPException(status_code=404, detail="E3 review has not run yet.")
    return result


@router.post("/{opportunity_id}/review/rerun")
def rerun_e3_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Re-trigger the E3 reviewer without re-running the full engine."""
    from app.config import get_settings
    settings = get_settings()
    _, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    e3_data = outputs.e3.model_dump(mode="json") if outputs.e3 else None
    if not e3_data:
        raise HTTPException(status_code=404, detail="E3 has not been run yet.")
    review_result = run_e3_reviewer(e3_data, settings.anthropic_api_key)
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    outputs["review_e3"] = review_result
    pipeline.step_outputs = serialize_pipeline_state_outputs(outputs)
    db.commit()
    return review_result


class E3RevisionRequest(BaseModel):
    engineer_notes: str = ""


def _get_e3_revision_count(pipeline: PipelineState) -> int:
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs)
    counts = outputs.revision_counts
    return counts.get("e3", 0)


def _increment_e3_revision_count(pipeline: PipelineState) -> int:
    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    counts = dict(outputs.get("revision_counts", {}))
    counts["e3"] = counts.get("e3", 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = serialize_pipeline_state_outputs(outputs)
    return counts["e3"]


@router.post("/{opportunity_id}/checkpoint/revise")
def revise_e3_checkpoint(
    opportunity_id: str,
    body: E3RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an E3 revision request. Max 3 revisions.
    Engineer must re-submit via the Proposal Generator to apply changes.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 23:
        raise HTTPException(
            status_code=409,
            detail="E3 not yet complete. Generate the proposal first.",
        )
    if opportunity.status == "complete":
        raise HTTPException(
            status_code=409,
            detail="E3 checkpoint already approved. Revisions are no longer possible.",
        )

    current_count = _get_e3_revision_count(pipeline)
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for E3. "
                   "Edit output files manually before approving.",
        )

    new_count = _increment_e3_revision_count(pipeline)

    outputs = deserialize_pipeline_state_outputs(pipeline.step_outputs).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"e3_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes
    pipeline.step_outputs = serialize_pipeline_state_outputs(outputs)
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "message": "Revision recorded. Re-run E3 via the Proposal Generator to apply changes.",
        "rerun_url": f"/e3?session_id={opportunity_id}",
    }
