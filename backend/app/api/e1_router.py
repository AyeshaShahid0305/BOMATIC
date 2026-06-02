import asyncio
import dataclasses
import functools
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
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
from app.engines.e1.step5_eval_criteria_extractor import extract_evaluation_criteria
from app.engines.e1.step8_sector_detector import detect_sector
from app.engines.e1.step9_framework_selector import select_frameworks
from app.engines.e1.step10_matrix_generator import generate_compliance_matrix
from app.engines.e1.step11_tp_linker import link_tp_sections
from app.engines.e1.step12_xlsx_writer import write_compliance_matrix_xlsx
from app.engines.e1.step13_requirements_docx_writer import write_requirements_docx
from app.api.reviewer import run_cp1_reviewer, run_cp2_reviewer
from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.schemas.pipeline import E1Output

"""E1 Pipeline — Step Numbering
Steps 1–4  (run_e1_pipeline):       file intake, classification, extraction, legal trap detection
Steps 5–7  (reserved):              numbers reserved for future steps — risk scoring, keyword enrichment,
                                     requirement deduplication — not yet designed or implemented
Steps 8–11 (checkpoint1_approve):   sector detection, framework selection, compliance matrix generation,
                                     TP section linking
Step 12    (checkpoint2_approve):   XLSX compliance matrix writer

step_outputs keys match step numbers. Keys 5, 6, 7 are intentionally absent.
"""

_DATA_DIR = Path(__file__).parent.parent / "data" / "frameworks"
_KNOWN_VENDORS = [
    "Cisco",
    "Fortinet",
    "Aruba",
    "Juniper",
    "Palo Alto",
    "Huawei",
    "Dell",
    "HPE",
    "HP",
    "Meraki",
    "Microsoft",
    "Splunk",
]


class MatrixRowPatch(BaseModel):
    status: str | None = None
    notes: str | None = None

router = APIRouter(prefix="/e1", tags=["e1"])


def _extract_vendor_list(texts: dict[str, str], requirements: list[dict]) -> list[str]:
    haystack = "\n".join(texts.values())
    haystack += "\n" + "\n".join(req.get("text", "") for req in requirements)
    vendors = [
        vendor
        for vendor in _KNOWN_VENDORS
        if re.search(rf"\b{re.escape(vendor)}\b", haystack, re.IGNORECASE)
    ]
    return sorted(set(vendors), key=str.lower)


def _build_e1_output(
    *,
    texts: dict[str, str],
    requirements: list[dict],
    risk_flags: list[dict],
    sector: str = "",
    frameworks_selected: list[str] | None = None,
) -> dict:
    output = E1Output(
        vendor_list=_extract_vendor_list(texts, requirements),
        requirements_baseline=requirements,
        risk_flags=risk_flags,
        sector=sector,
        frameworks_selected=frameworks_selected or [],
    )
    return output.model_dump()


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

    # Write extracted text back to Document records so E2/E3/E4/E5 can read it.
    for doc in documents:
        if doc.filename in texts:
            doc.text_content = texts[doc.filename]

    # Steps 2–4: analysis on extracted text
    classified_for_step2 = [{"filename": r["filename"], "type": r["type"]} for r in step1_results]
    missing   = detect_missing_documents(classified_for_step2, texts)
    reqs      = extract_requirements(texts, opportunity_id=opportunity_id)
    flags         = detect_legal_traps(texts)
    eval_criteria = extract_evaluation_criteria(texts)
    requirements_payload = [dataclasses.asdict(r) for r in reqs]
    flags_payload = [dataclasses.asdict(f) for f in flags]

    # Persist: assign new dict so SQLAlchemy detects the change on the JSONB column
    pipeline.step_outputs = {
        **pipeline.step_outputs,
        "1": step1_results,
        "2": [dataclasses.asdict(m) for m in missing],
        "3": requirements_payload,
        "4": flags_payload,
        "5": eval_criteria,
        "e1": _build_e1_output(
            texts=texts,
            requirements=requirements_payload,
            risk_flags=flags_payload,
        ),
    }
    pipeline.current_step = 4
    opportunity.status = "checkpoint_1_pending"

    # Run automated reviewer before engineer sees Checkpoint 1
    review_result = run_cp1_reviewer(pipeline.step_outputs, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_cp1": review_result}

    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "current_step": 4,
        "files": step1_results,
        "requirements": requirements_payload,
        "missing_docs": [dataclasses.asdict(m) for m in missing],
        "flags": flags_payload,
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
async def checkpoint1_approve(opportunity_id: str, db: Session = Depends(get_db)):
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

    # Step 8: sector detection
    documents = db.query(Document).filter(Document.opportunity_id == opportunity.id).all()
    texts = {doc.filename: doc.text_content for doc in documents if doc.text_content}
    sector_result = detect_sector(client_name, texts)

    # Step 9: framework selection
    related_standards: list[str] = []
    for req in requirements:
        related_standards.extend(req.get("related_standards", []))
    frameworks = select_frameworks(sector_result["sector"], related_standards)

    # Step 10: compliance matrix generation (AI call inside — offloaded to threadpool)
    matrix_result = await asyncio.get_running_loop().run_in_executor(
        None,
        functools.partial(
            generate_compliance_matrix,
            requirements=requirements,
            frameworks=frameworks,
            api_key=settings.anthropic_api_key,
            data_dir=_DATA_DIR,
        ),
    )

    # Step 11: TP section linking
    link_tp_sections(matrix_result["matrix_rows"])

    # Persist
    e1_existing = pipeline.step_outputs.get("e1", {})
    e1_requirements = e1_existing.get("requirements_baseline") or requirements
    e1_risk_flags = e1_existing.get("risk_flags") or pipeline.step_outputs.get("4", [])
    pipeline.step_outputs = {
        **pipeline.step_outputs,
        "8": sector_result,
        "9": frameworks,
        "10": matrix_result["matrix_rows"],
        "gaps": matrix_result["gaps"],
        "stats": matrix_result["stats"],
        "e1": _build_e1_output(
            texts=texts,
            requirements=e1_requirements,
            risk_flags=e1_risk_flags,
            sector=sector_result["sector"],
            frameworks_selected=frameworks,
        ),
    }
    pipeline.current_step = 11
    opportunity.status = "checkpoint_2_pending"

    # Run automated reviewer before engineer sees Checkpoint 2
    review_result = run_cp2_reviewer(pipeline.step_outputs, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_cp2": review_result}

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
async def checkpoint2_approve(opportunity_id: str, db: Session = Depends(get_db)):
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
    xlsx_path = await asyncio.get_running_loop().run_in_executor(
        None,
        functools.partial(
            write_compliance_matrix_xlsx,
            matrix_rows=matrix_rows,
            gaps=gaps,
            stats=stats,
            opportunity_id=opportunity_id,
            output_dir=output_dir,
        ),
    )

    # Generate requirements baseline DOCX alongside the compliance matrix
    requirements: list[dict] = pipeline.step_outputs.get("3", [])
    requirements_docx_path = write_requirements_docx(
        requirements=requirements,
        opportunity_id=opportunity_id,
        project_name=opportunity.project_name or opportunity_id,
        output_dir=output_dir,
    )

    pipeline.step_outputs = {
        **pipeline.step_outputs,
        "xlsx_path": str(xlsx_path),
        "requirements_docx_path": str(requirements_docx_path),
    }
    pipeline.current_step = 12
    opportunity.status = "e1_complete"
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


def _get_revision_count(pipeline: PipelineState, checkpoint: str) -> int:
    """Return the current revision count for a checkpoint key ('cp1' or 'cp2')."""
    counts = (pipeline.step_outputs or {}).get("revision_counts", {})
    return counts.get(checkpoint, 0)


def _increment_revision_count(pipeline: PipelineState, checkpoint: str) -> int:
    """
    Increment the revision count for the given checkpoint in step_outputs.
    Returns the NEW count after incrementing.
    Assigns a new dict to step_outputs so SQLAlchemy detects the JSONB change.
    """
    outputs = dict(pipeline.step_outputs or {})
    counts = dict(outputs.get("revision_counts", {}))
    counts[checkpoint] = counts.get(checkpoint, 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = outputs
    return counts[checkpoint]


class RevisionRequest(BaseModel):
    engineer_notes: str = ""


@router.post("/{opportunity_id}/checkpoint1/revise")
async def checkpoint1_revise(
    opportunity_id: str,
    body: RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Re-run Steps 3-4 (requirements extraction + legal trap detection) and update
    step_outputs. Max 3 revisions. Returns 409 on the 4th attempt.

    The engineer_notes are stored in step_outputs["revision_notes"]["cp1"] for
    audit purposes but do not alter the deterministic step logic.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 4:
        raise HTTPException(
            status_code=409,
            detail="Steps 1-4 not yet completed. Run the pipeline first.",
        )
    if pipeline.current_step >= 11:
        raise HTTPException(
            status_code=409,
            detail="Checkpoint 1 already approved. Revisions are no longer possible.",
        )

    current_count = _get_revision_count(pipeline, "cp1")
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for Checkpoint 1. Edit output files manually before approving.",
        )

    documents = db.query(Document).filter(Document.opportunity_id == opportunity.id).all()
    texts: dict[str, str] = {
        doc.filename: doc.text_content
        for doc in documents
        if doc.text_content
    }
    if not texts:
        raise HTTPException(
            status_code=400,
            detail="No extracted text found. Re-upload the RFP package.",
        )

    reqs = extract_requirements(texts, opportunity_id=opportunity_id)
    flags = detect_legal_traps(texts)

    requirements_payload = [dataclasses.asdict(r) for r in reqs]
    flags_payload = [dataclasses.asdict(f) for f in flags]

    new_count = _increment_revision_count(pipeline, "cp1")

    outputs = dict(pipeline.step_outputs)

    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"cp1_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes

    outputs["3"] = requirements_payload
    outputs["4"] = flags_payload

    e1_existing = outputs.get("e1", {})
    outputs["e1"] = _build_e1_output(
        texts=texts,
        requirements=requirements_payload,
        risk_flags=flags_payload,
        sector=e1_existing.get("sector", ""),
        frameworks_selected=e1_existing.get("frameworks_selected", []),
    )

    pipeline.step_outputs = outputs
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "requirements_count": len(requirements_payload),
        "flags_count": len(flags_payload),
        "step_outputs": {
            "3": requirements_payload,
            "4": flags_payload,
        },
    }


@router.post("/{opportunity_id}/checkpoint2/revise")
async def checkpoint2_revise(
    opportunity_id: str,
    body: RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Re-run Steps 8-11 (sector detection, framework selection, compliance matrix
    generation, TP section linking) and update step_outputs.
    Max 3 revisions. Returns 409 on the 4th attempt.
    """
    MAX_REVISIONS = 3
    settings = get_settings()

    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=409,
            detail="Checkpoint 1 not yet approved. Complete Checkpoint 1 first.",
        )
    if pipeline.current_step >= 12:
        raise HTTPException(
            status_code=409,
            detail="Checkpoint 2 already approved. Revisions are no longer possible.",
        )

    current_count = _get_revision_count(pipeline, "cp2")
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for Checkpoint 2. Edit output files manually before approving.",
        )

    requirements: list[dict] = (pipeline.step_outputs or {}).get("3", [])
    if not requirements:
        raise HTTPException(
            status_code=400,
            detail="No requirements found in pipeline state. Re-run and approve Checkpoint 1 first.",
        )

    documents = db.query(Document).filter(Document.opportunity_id == opportunity.id).all()
    texts: dict[str, str] = {
        doc.filename: doc.text_content
        for doc in documents
        if doc.text_content
    }

    client_name = opportunity.client_name or ""

    sector_result = detect_sector(client_name, texts)

    related_standards: list[str] = []
    for req in requirements:
        related_standards.extend(req.get("related_standards", []))
    frameworks = select_frameworks(sector_result["sector"], related_standards)

    matrix_result = await asyncio.get_running_loop().run_in_executor(
        None,
        functools.partial(
            generate_compliance_matrix,
            requirements=requirements,
            frameworks=frameworks,
            api_key=settings.anthropic_api_key,
            data_dir=_DATA_DIR,
        ),
    )

    link_tp_sections(matrix_result["matrix_rows"])

    new_count = _increment_revision_count(pipeline, "cp2")

    outputs = dict(pipeline.step_outputs)

    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"cp2_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes

    outputs["8"] = sector_result
    outputs["9"] = frameworks
    outputs["10"] = matrix_result["matrix_rows"]
    outputs["gaps"] = matrix_result["gaps"]
    outputs["stats"] = matrix_result["stats"]

    e1_existing = outputs.get("e1", {})
    outputs["e1"] = _build_e1_output(
        texts=texts,
        requirements=e1_existing.get("requirements_baseline") or requirements,
        risk_flags=e1_existing.get("risk_flags") or outputs.get("4", []),
        sector=sector_result["sector"],
        frameworks_selected=frameworks,
    )

    pipeline.step_outputs = outputs
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "matrix_row_count": len(matrix_result["matrix_rows"]),
        "stats": matrix_result["stats"],
    }


# ---------------------------------------------------------------------------
# Reviewer routes
# ---------------------------------------------------------------------------

@router.get("/{opportunity_id}/review/{checkpoint}")
def get_review_result(
    opportunity_id: str,
    checkpoint: str,
    db: Session = Depends(get_db),
):
    """
    Return the stored review result for a checkpoint.
    checkpoint must be 'cp1' or 'cp2'.
    Returns 404 if the reviewer has not yet run for this checkpoint.
    """
    if checkpoint not in ("cp1", "cp2"):
        raise HTTPException(status_code=400, detail="checkpoint must be 'cp1' or 'cp2'.")

    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    key = f"review_{checkpoint}"
    result = (pipeline.step_outputs or {}).get(key)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Review for {checkpoint} has not run yet.",
        )
    return result


@router.post("/{opportunity_id}/review/{checkpoint}/rerun")
async def rerun_review(
    opportunity_id: str,
    checkpoint: str,
    db: Session = Depends(get_db),
):
    """
    Re-trigger the reviewer for a checkpoint without re-running the full engine.
    Useful after an engineer manually edits the output before approving.
    checkpoint must be 'cp1' or 'cp2'.
    """
    if checkpoint not in ("cp1", "cp2"):
        raise HTTPException(status_code=400, detail="checkpoint must be 'cp1' or 'cp2'.")

    settings = get_settings()
    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    step_outputs = pipeline.step_outputs or {}

    if checkpoint == "cp1":
        if pipeline.current_step < 4:
            raise HTTPException(status_code=409, detail="Steps 1-4 not yet completed.")
        review_result = run_cp1_reviewer(step_outputs, settings.anthropic_api_key)
        key = "review_cp1"
    else:
        if pipeline.current_step < 11:
            raise HTTPException(status_code=409, detail="Checkpoint 1 not yet approved.")
        review_result = run_cp2_reviewer(step_outputs, settings.anthropic_api_key)
        key = "review_cp2"

    pipeline.step_outputs = {**step_outputs, key: review_result}
    db.commit()

    return review_result
