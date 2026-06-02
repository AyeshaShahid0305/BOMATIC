import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db import get_db
from app.engines.e2.step1_rfp_extractor import extract_rfp_requirements
from app.engines.e2.step3_catalog_matcher import match_catalog
from app.engines.e2.step4_gap_analyzer import analyze_gaps
from app.engines.e3 import run_e3_pipeline
from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e3" / "output"

router = APIRouter(prefix="/e3", tags=["e3"])


@router.post("/generate")
async def generate_proposal(
    rfp_session_id: str = Form(...),
    gbb_tier: str = Form("better"),
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
    persisted_e2 = (pipeline_state.step_outputs or {}).get('e2') if pipeline_state else None
    pricing_summary = None

    if persisted_e2:
        pricing_summary = persisted_e2
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
            pricing_summary = analyze_gaps(matches)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    try:
        result = run_e3_pipeline(rfp_session_id, db, gbb_tier, pricing_summary)
        if pipeline_state:
            outputs = dict(pipeline_state.step_outputs or {})
            outputs['e3'] = {
                'project_name': result.get('project_name', ''),
                'section_count': result.get('section_count', 0),
                'output_file': result.get('output_file', ''),
                'pdf_file': result.get('pdf_file') or '',
            }
            pipeline_state.step_outputs = outputs
            pipeline_state.current_step = max(pipeline_state.current_step, 23)
            opportunity.status = 'e3_complete'
            flag_modified(pipeline_state, 'step_outputs')
            db.commit()
        return result
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
    e3_data = (pipeline.step_outputs or {}).get("e3")
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
