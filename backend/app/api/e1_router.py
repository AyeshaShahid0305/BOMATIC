import dataclasses
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.engines.e1.extractors import extract_text
from app.engines.e1.step1_classifier import classify_file
from app.engines.e1.step2_missing_docs import detect_missing_documents
from app.engines.e1.step3_requirements_extractor import extract_requirements
from app.engines.e1.step4_legal_trap_flagger import detect_legal_traps
from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState

router = APIRouter(prefix="/e1", tags=["e1"])


@router.post("/analyze")
async def analyze_rfp(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        classified: list[dict] = []
        texts: dict[str, str] = {}

        for upload in files:
            name = Path(upload.filename or "file").name
            dest = tmp_dir / name
            if upload.size is not None and upload.size > 20 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large. Maximum size is 20MB.")
            dest.write_bytes(await upload.read())

            classification = classify_file(
                filename=name,
                folder_path="",
                file_path=dest,
            )
            classified.append({"filename": name, "type": classification.type})

            extracted = extract_text(dest)
            if extracted.get("text"):
                texts[name] = extracted["text"]

        missing   = detect_missing_documents(classified, texts)
        reqs      = extract_requirements(texts, opportunity_id="analyze")
        flags     = detect_legal_traps(texts)

        return {
            "files": [
                {"name": c["filename"], "type": c["type"]}
                for c in classified
            ],
            "requirements": [
                {"text": r.text, "confidence": r.confidence, "type": r.classification}
                for r in reqs
            ],
            "flags": [
                {"flag": f.flag, "severity": f.severity, "deadline": f.deadline}
                for f in flags
            ],
            "missing_docs": [
                {"name": m.referenced_doc, "severity": m.severity, "action": m.action}
                for m in missing
            ],
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/{opportunity_id}/run")
def run_e1_pipeline(opportunity_id: str, db: Session = Depends(get_db)):
    """
    Run Steps 1–4 on an already-uploaded RFP package and persist results.

    Reads files from storage/, runs the four analysis steps, saves output to
    pipeline_state.step_outputs, and advances current_step to 4.
    Returns 409 if Steps 1–4 have already been run for this opportunity.
    """
    settings = get_settings()

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
        raise HTTPException(status_code=404, detail="Pipeline state not found for this opportunity.")

    if pipeline.current_step >= 4:
        raise HTTPException(
            status_code=409,
            detail=f"Steps 1–4 already completed (current_step={pipeline.current_step}). Retrieve state via GET /{opportunity_id}/state.",
        )

    documents = (
        db.query(Document)
        .filter(Document.opportunity_id == opportunity.id)
        .all()
    )
    if not documents:
        raise HTTPException(status_code=400, detail="No documents found for this opportunity.")

    package_dir = Path(settings.upload_dir) / opportunity_id

    # Step 1: classify each file and extract text
    step1_results: list[dict] = []
    texts: dict[str, str] = {}

    for doc in documents:
        file_path = package_dir / doc.filename
        if not file_path.exists():
            continue

        classification = classify_file(
            filename=doc.filename,
            folder_path="",
            file_path=file_path,
        )
        step1_results.append({"filename": doc.filename, **dataclasses.asdict(classification)})

        extracted = extract_text(file_path)
        if extracted.get("text"):
            texts[doc.filename] = extracted["text"]

    if not step1_results:
        raise HTTPException(status_code=400, detail="No readable files found in the package directory.")

    # Steps 2–4: analysis on extracted text
    classified_for_step2 = [{"filename": r["filename"], "type": r["type"]} for r in step1_results]
    missing   = detect_missing_documents(classified_for_step2, texts)
    reqs      = extract_requirements(texts, opportunity_id=opportunity_id)
    flags     = detect_legal_traps(texts)

    # Persist: assign new dict so SQLAlchemy detects the change on the JSONB column
    pipeline.step_outputs = {
        **pipeline.step_outputs,
        "1": step1_results,
        "2": [dataclasses.asdict(m) for m in missing],
        "3": [dataclasses.asdict(r) for r in reqs],
        "4": [dataclasses.asdict(f) for f in flags],
    }
    pipeline.current_step = 4
    opportunity.status = "checkpoint_1_pending"
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "current_step": 4,
        "files": step1_results,
        "requirements": [dataclasses.asdict(r) for r in reqs],
        "missing_docs": [dataclasses.asdict(m) for m in missing],
        "flags": [dataclasses.asdict(f) for f in flags],
    }


@router.get("/{opportunity_id}/state")
def get_pipeline_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the full pipeline state for a given opportunity."""
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
        raise HTTPException(status_code=404, detail="Pipeline state not found for this opportunity.")

    return {
        "opportunity_id": opportunity_id,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "step_outputs": pipeline.step_outputs,
        "updated_at": pipeline.updated_at.isoformat(),
    }
