import dataclasses
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.engines.e1.extractors import extract_text
from app.engines.e1.step1_classifier import classify_file
from app.engines.e1.step2_missing_docs import detect_missing_documents
from app.engines.e1.step3_requirements_extractor import extract_requirements
from app.engines.e1.step4_legal_trap_flagger import detect_legal_traps
from app.engines.e1.step8_sector_detector import detect_sector
from app.engines.e1.step9_framework_selector import select_frameworks
from app.engines.e1.step10_matrix_generator import generate_compliance_matrix
from app.engines.e1.step11_tp_linker import link_tp_sections
from app.engines.e1.step12_xlsx_writer import write_compliance_matrix_xlsx
from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState

_DATA_DIR = Path(__file__).parent.parent / "data" / "frameworks"


class MatrixRowPatch(BaseModel):
    status: str | None = None
    notes: str | None = None

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


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _get_opportunity_and_pipeline(opportunity_id: str, db: Session):
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

    return opportunity, pipeline


# ---------------------------------------------------------------------------
# Checkpoint 1 — approve and run Steps 8–11
# ---------------------------------------------------------------------------

@router.post("/{opportunity_id}/checkpoint1/approve")
def checkpoint1_approve(opportunity_id: str, db: Session = Depends(get_db)):
    """
    Approve Checkpoint 1: run Steps 8–11 (sector, frameworks, matrix, TP links)
    and advance pipeline to step 11 (checkpoint_2_pending).
    """
    settings = get_settings()
    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 4:
        raise HTTPException(
            status_code=409,
            detail=f"Steps 1–4 not yet completed (current_step={pipeline.current_step}). Run POST /{opportunity_id}/run first.",
        )
    if pipeline.current_step >= 11:
        raise HTTPException(
            status_code=409,
            detail=f"Checkpoint 1 already approved (current_step={pipeline.current_step}).",
        )

    requirements: list[dict] = pipeline.step_outputs.get("3", [])
    if not requirements:
        raise HTTPException(status_code=400, detail="No requirements found in pipeline state. Re-run Steps 1–4.")

    client_name = opportunity.client_name or ""

    # Step 8: sector detection from client name (texts empty — already stored)
    sector_result = detect_sector(client_name, {})

    # Step 9: framework selection
    related_standards: list[str] = []
    for req in requirements:
        related_standards.extend(req.get("related_standards", []))
    frameworks = select_frameworks(sector_result["sector"], related_standards)

    # Step 10: compliance matrix generation (AI call inside)
    matrix_result = generate_compliance_matrix(
        requirements=requirements,
        frameworks=frameworks,
        api_key=settings.anthropic_api_key,
        data_dir=_DATA_DIR,
    )

    # Step 11: TP section linking
    link_tp_sections(matrix_result["matrix_rows"])

    # Persist
    pipeline.step_outputs = {
        **pipeline.step_outputs,
        "8": sector_result,
        "9": frameworks,
        "10": matrix_result["matrix_rows"],
        "gaps": matrix_result["gaps"],
        "stats": matrix_result["stats"],
    }
    pipeline.current_step = 11
    opportunity.status = "checkpoint_2_pending"
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "current_step": 11,
        "sector": sector_result,
        "frameworks": frameworks,
        "stats": matrix_result["stats"],
    }


# ---------------------------------------------------------------------------
# Checkpoint 2 — approve and write Excel output
# ---------------------------------------------------------------------------

@router.post("/{opportunity_id}/checkpoint2/approve")
def checkpoint2_approve(opportunity_id: str, db: Session = Depends(get_db)):
    """
    Approve Checkpoint 2: write the compliance matrix .xlsx and mark pipeline complete.
    """
    settings = get_settings()
    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=409,
            detail=f"Checkpoint 1 not yet approved (current_step={pipeline.current_step}).",
        )

    matrix_rows: list[dict] = pipeline.step_outputs.get("10", [])
    gaps: dict = pipeline.step_outputs.get("gaps", {"coverage_gaps": [], "orphan_requirements": []})
    stats: dict = pipeline.step_outputs.get("stats", {})

    output_dir = Path(settings.upload_dir) / opportunity_id
    xlsx_path = write_compliance_matrix_xlsx(
        matrix_rows=matrix_rows,
        gaps=gaps,
        stats=stats,
        opportunity_id=opportunity_id,
        output_dir=output_dir,
    )

    pipeline.step_outputs = {
        **pipeline.step_outputs,
        "xlsx_path": str(xlsx_path),
    }
    pipeline.current_step = 12
    opportunity.status = "complete"
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "current_step": 12,
        "download_url": f"/e1/{opportunity_id}/download/matrix",
    }


# ---------------------------------------------------------------------------
# Matrix read and download
# ---------------------------------------------------------------------------

@router.get("/{opportunity_id}/matrix")
def get_matrix(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the generated compliance matrix rows, gaps, and stats."""
    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=404,
            detail="Compliance matrix not yet generated. Complete Checkpoint 1 first.",
        )

    return {
        "opportunity_id": opportunity_id,
        "matrix_rows": pipeline.step_outputs.get("10", []),
        "gaps": pipeline.step_outputs.get("gaps", {}),
        "stats": pipeline.step_outputs.get("stats", {}),
    }


@router.get("/{opportunity_id}/download/matrix")
def download_matrix(opportunity_id: str, db: Session = Depends(get_db)):
    """Download the compliance matrix .xlsx file."""
    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    xlsx_path_str: str = pipeline.step_outputs.get("xlsx_path", "")
    if not xlsx_path_str:
        raise HTTPException(
            status_code=404,
            detail="Excel file not yet generated. Complete Checkpoint 2 first.",
        )

    xlsx_path = Path(xlsx_path_str)
    if not xlsx_path.exists():
        raise HTTPException(status_code=404, detail="Excel file not found on disk.")

    return FileResponse(
        path=str(xlsx_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=xlsx_path.name,
    )


@router.patch("/{opportunity_id}/matrix/{req_id}")
def patch_matrix_row(
    opportunity_id: str,
    req_id: str,
    body: MatrixRowPatch,
    db: Session = Depends(get_db),
):
    """Partially update status and/or notes for all matrix rows matching req_id."""
    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=404,
            detail="Compliance matrix not yet generated. Complete Checkpoint 1 first.",
        )

    matrix_rows: list[dict] = pipeline.step_outputs.get("10", [])

    matching = [r for r in matrix_rows if r.get("req_id") == req_id]
    if not matching:
        raise HTTPException(status_code=404, detail=f"No matrix row found with req_id '{req_id}'.")

    update = body.model_dump(exclude_none=True)
    for row in matrix_rows:
        if row.get("req_id") == req_id:
            row.update(update)

    # Assign a new dict so SQLAlchemy detects the change on the JSONB column
    pipeline.step_outputs = {**pipeline.step_outputs, "10": matrix_rows}
    db.commit()

    return matching[0]
