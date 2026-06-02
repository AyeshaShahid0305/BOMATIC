import os
import re
import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Form, Header, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.db import get_db
from app.config import get_settings
from app.models.opportunity import Opportunity
from app.models.document import Document
from app.models.pipeline_state import PipelineState

router = APIRouter(tags=["rfp"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".dwg", ".msg", ".doc"}
VALID_OPPORTUNITY_MODES = {"rfp", "rfi"}
ALL_ENGINE_STATUSES = [
    "e1_pending",
    "e1_complete",
    "e2_pending",
    "e2_complete",
    "e3_pending",
    "e3_complete",
    "e4_pending",
    "e4_complete",
    "e5_pending",
    "e5_complete",
]


def _derive_opportunity_status(mode: str, current_step: int) -> str:
    if mode == "rfi":
        if current_step < 4:
            return "e4_pending"
        if current_step <= 10:
            return "e4_pending"
        if current_step == 11:
            return "e4_complete"
        if current_step <= 20:
            return "e5_pending"
        if current_step == 21:
            return "e5_complete"
        if current_step == 22:
            return "e2_complete"
        return "e3_complete"

    if current_step < 4:
        return "e1_pending"
    if current_step < 12:
        return "e1_pending"
    if current_step == 12:
        return "e1_complete"
    if current_step < 21:
        return "e2_pending"
    if current_step == 21:
        return "e2_complete"
    return "e3_complete"


def _get_file_format(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return ext.lstrip(".") if ext else "unknown"


def _output_dirs() -> dict[str, Path]:
    app_dir = Path(__file__).resolve().parents[1]
    return {
        "e2": app_dir / "engines" / "e2" / "output",
        "e3": app_dir / "engines" / "e3" / "output",
        "e4": app_dir / "engines" / "e4" / "output",
        "e5": app_dir / "engines" / "e5" / "output",
    }


def _reject_unsafe_filename(filename: str) -> None:
    path = Path(filename)
    if filename != path.name or ".." in path.parts or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")


def _collect_outputs(pipeline: PipelineState | None) -> list[dict]:
    if not pipeline:
        return []

    outputs = pipeline.step_outputs or {}
    output_dirs = _output_dirs()
    files: list[dict] = []

    def add_file(engine: str, label: str, filename: str, path: Path) -> None:
        if path.exists() and path.is_file():
            files.append(
                {
                    "engine": engine,
                    "label": label,
                    "filename": filename,
                    "actual_filename": path.name,
                    "size_bytes": path.stat().st_size,
                }
            )

    xlsx_path = outputs.get("xlsx_path")
    if xlsx_path:
        add_file("E1", "Compliance Matrix", "compliance_matrix.xlsx", Path(xlsx_path))

    req_docx_path = outputs.get("requirements_docx_path")
    if req_docx_path:
        add_file("E1", "Requirements Baseline", "requirements.docx", Path(req_docx_path))

    for key, engine, label, canonical_name in [
        ("e2", "E2", "BoM Workbook", "bom_workbook.xlsx"),
        ("e3", "E3", "Technical Proposal", "technical_proposal.docx"),
        ("e4", "E4", "RFI Questionnaire", "rfi_questionnaire.xlsx"),
        ("e5", "E5", "Design Document", "design_document.docx"),
    ]:
        output_file = (outputs.get(key) or {}).get("output_file")
        if output_file:
            add_file(engine, label, canonical_name, output_dirs[key] / Path(output_file).name)

    # E2 Distributor Export
    e2_distributor = (outputs.get("e2") or {}).get("distributor_file")
    if e2_distributor:
        add_file("E2", "Distributor Export", "distributor_export.xlsx", output_dirs["e2"] / Path(e2_distributor).name)

    # Submission PDF (generated alongside the E3 DOCX)
    e3_pdf = (outputs.get("e3") or {}).get("pdf_file")
    if e3_pdf:
        add_file("E3", "Submission PDF", "submission.pdf", output_dirs["e3"] / Path(e3_pdf).name)

    return files


def _resolve_output_path(pipeline: PipelineState | None, filename: str) -> tuple[Path, str]:
    _reject_unsafe_filename(filename)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Output file not found.")

    outputs = pipeline.step_outputs or {}
    output_dirs = _output_dirs()
    candidates: dict[str, Path] = {}

    xlsx_path = outputs.get("xlsx_path")
    if xlsx_path:
        path = Path(xlsx_path)
        candidates["compliance_matrix.xlsx"] = path
        candidates[path.name] = path

    req_docx_path = outputs.get("requirements_docx_path")
    if req_docx_path:
        path = Path(req_docx_path)
        candidates["requirements.docx"] = path
        candidates[path.name] = path

    for key, canonical_name in [
        ("e2", "bom_workbook.xlsx"),
        ("e3", "technical_proposal.docx"),
        ("e4", "rfi_questionnaire.xlsx"),
        ("e5", "design_document.docx"),
    ]:
        output_file = (outputs.get(key) or {}).get("output_file")
        if output_file:
            actual_name = Path(output_file).name
            path = output_dirs[key] / actual_name
            candidates[canonical_name] = path
            candidates[actual_name] = path

    # E2 Distributor Export
    e2_distributor = (outputs.get("e2") or {}).get("distributor_file")
    if e2_distributor:
        actual_name = Path(e2_distributor).name
        path = output_dirs["e2"] / actual_name
        candidates["distributor_export.xlsx"] = path
        candidates[actual_name] = path

    # Submission PDF
    e3_pdf = (outputs.get("e3") or {}).get("pdf_file")
    if e3_pdf:
        actual_name = Path(e3_pdf).name
        path = output_dirs["e3"] / actual_name
        candidates["submission.pdf"] = path
        candidates[actual_name] = path

    path = candidates.get(filename)
    if not path or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Output file not found.")

    return path, filename


@router.post("/rfp/packages", status_code=status.HTTP_201_CREATED)
async def upload_rfp_package(
    files: list[UploadFile] = File(...),
    opportunity_id: Optional[str] = Form(None),
    client_name: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    mode: Optional[str] = Form("rfp"),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Upload an RFP package (1–100 files).

    Think of this as the entry point to the E1 pipeline:
    files land here → stored on disk → DB records created → pipeline clock starts at step 0.
    """
    settings = get_settings()

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per package.")

    for upload in files:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' is not allowed. Accepted types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

    for upload in files:
        if upload.size is not None and upload.size > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File '{upload.filename}' exceeds the 20 MB limit.",
            )
    total_size = sum(u.size for u in files if u.size is not None)
    if total_size > 200 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"Total upload size {total_size // (1024*1024)} MB exceeds the 200 MB per-package limit.",
        )
    mode_value = (mode or "rfp").strip().lower()
    if mode_value not in VALID_OPPORTUNITY_MODES:
        raise HTTPException(status_code=400, detail="mode must be either 'rfp' or 'rfi'.")


    # Use provided opportunity_id or generate one
    opp_id_str = opportunity_id or f"OPP-{uuid.uuid4().hex[:8].upper()}"

    if not re.match(r'^[A-Z0-9][A-Z0-9\-]{0,63}$', opp_id_str):
        raise HTTPException(
            status_code=400,
            detail="opportunity_id may only contain uppercase letters, digits, and hyphens (A-Z, 0-9, -). No dots, slashes, or special characters.",
        )

    # Reject if opportunity_id already exists
    existing = db.query(Opportunity).filter(Opportunity.opportunity_id == opp_id_str).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Opportunity '{opp_id_str}' already exists. Use a different ID or retrieve the existing package.",
        )

    # Create storage directory for this package
    package_dir = os.path.join(settings.upload_dir, opp_id_str)
    os.makedirs(package_dir, exist_ok=True)

    # Resolve owner from JWT if provided
    owner_id: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            owner_id = payload.get("sub")
        except JWTError:
            pass  # Invalid token - treat as anonymous upload

    # Persist opportunity
    opportunity = Opportunity(
        opportunity_id=opp_id_str,
        client_name=client_name,
        project_name=project_name,
        mode=mode_value,
        status="uploaded",
        user_id=owner_id,
    )
    db.add(opportunity)
    db.flush()  # get opportunity.id without committing yet

    # Save each file and create a Document record
    saved_documents = []
    for upload in files:
        original_filename = upload.filename or f"file_{uuid.uuid4().hex[:6]}"
        safe_filename = os.path.basename(original_filename)  # strip any path traversal
        file_path = os.path.join(package_dir, safe_filename)
        if os.path.exists(file_path):
            base, ext = os.path.splitext(safe_filename)
            counter = 1
            while os.path.exists(file_path):
                safe_filename = f"{base}_{counter}{ext}"
                file_path = os.path.join(package_dir, safe_filename)
                counter += 1

        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload.file, f)

        doc = Document(
            opportunity_id=opportunity.id,
            filename=safe_filename,
            file_path=os.path.join(opp_id_str, safe_filename),  # relative to storage/
            file_format=_get_file_format(safe_filename),
        )
        db.add(doc)
        saved_documents.append(safe_filename)

    # Create initial pipeline state (step 0 = not started)
    pipeline_state = PipelineState(opportunity_id=opportunity.id)
    db.add(pipeline_state)

    db.commit()

    return {
        "opportunity_id": opp_id_str,
        "document_count": len(saved_documents),
        "documents": saved_documents,
        "status": "uploaded",
        "mode": mode_value,
    }



@router.get("/opportunities")
def list_opportunities(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """Return opportunities. Filters by owner when a valid JWT is present."""
    owner_id: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            owner_id = payload.get("sub")
        except JWTError:
            pass

    query = (
        db.query(Opportunity, PipelineState)
        .join(PipelineState, PipelineState.opportunity_id == Opportunity.id)
        .order_by(Opportunity.created_at.desc())
    )

    if owner_id:
        query = query.filter(Opportunity.user_id == owner_id)

    rows = query.all()

    return [
        {
            "opportunity_id": opportunity.opportunity_id,
            "project_name": opportunity.project_name,
            "client_name": opportunity.client_name,
            "mode": opportunity.mode or "rfp",
            "status": _derive_opportunity_status(opportunity.mode or "rfp", pipeline.current_step),
            "status_options": ALL_ENGINE_STATUSES,
            "current_step": pipeline.current_step,
            "created_at": opportunity.created_at.isoformat(),
            "engines_completed": list((pipeline.step_outputs or {}).keys()),
        }
        for opportunity, pipeline in rows
    ]


@router.get("/rfp/packages/{opportunity_id}")
def get_rfp_package(opportunity_id: str, db: Session = Depends(get_db)):
    """Retrieve an uploaded RFP package with its document list and pipeline status."""
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == opportunity_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' not found.")

    documents = (
        db.query(Document)
        .filter(Document.opportunity_id == opportunity.id)
        .all()
    )

    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )

    return {
        "opportunity_id": opportunity.opportunity_id,
        "client_name": opportunity.client_name,
        "project_name": opportunity.project_name,
        "mode": opportunity.mode or "rfp",
        "status": _derive_opportunity_status(opportunity.mode or "rfp", pipeline.current_step if pipeline else 0),
        "pipeline_step": pipeline.current_step if pipeline else 0,
        "step_outputs": pipeline.step_outputs if pipeline else {},
        "created_at": opportunity.created_at.isoformat(),
        "documents": [
            {
                "filename": d.filename,
                "file_format": d.file_format,
                "doc_type": d.doc_type,
                "confidence": d.confidence,
            }
            for d in documents
        ],
    }


@router.get("/rfp/packages/{opportunity_id}/outputs")
def list_outputs(opportunity_id: str, db: Session = Depends(get_db)):
    """Return downloadable logical output files for an opportunity."""
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

    step_outputs = pipeline.step_outputs or {}
    outputs = []
    if step_outputs.get("xlsx_path"):
        outputs.append({"filename": "compliance_matrix.xlsx", "engine": "E1"})
    if step_outputs.get("requirements_docx_path"):
        outputs.append({"filename": "requirements.docx", "engine": "E1"})
    if (step_outputs.get("e2") or {}).get("output_file"):
        outputs.append({"filename": "bom_workbook.xlsx", "engine": "E2"})
    if (step_outputs.get("e2") or {}).get("distributor_file"):
        outputs.append({"filename": "distributor_export.xlsx", "engine": "E2"})
    if (step_outputs.get("e3") or {}).get("output_file"):
        outputs.append({"filename": "technical_proposal.docx", "engine": "E3"})
    if (step_outputs.get("e3") or {}).get("pdf_file"):
        outputs.append({"filename": "submission.pdf", "engine": "E3"})
    if (step_outputs.get("e5") or {}).get("output_file"):
        outputs.append({"filename": "hld_lld.docx", "engine": "E5"})

    return {"opportunity_id": opportunity_id, "outputs": outputs}


@router.api_route("/rfp/packages/{opportunity_id}/outputs/{filename:path}", methods=["GET", "HEAD"])
def download_output(opportunity_id: str, filename: str, db: Session = Depends(get_db)):
    """Download a generated engine output by logical filename."""
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

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

    step_outputs = pipeline.step_outputs or {}
    engines_dir = Path(__file__).parent.parent / "engines"

    if filename == "compliance_matrix.xlsx":
        raw = step_outputs.get("xlsx_path", "")
        if not raw:
            raise HTTPException(status_code=404, detail="E1 compliance matrix not yet generated.")
        file_path = Path(raw)
    elif filename == "requirements.docx":
        raw = step_outputs.get("requirements_docx_path", "")
        if not raw:
            raise HTTPException(status_code=404, detail="E1 requirements baseline not yet generated.")
        file_path = Path(raw)
    elif filename == "bom_workbook.xlsx":
        actual = (step_outputs.get("e2") or {}).get("output_file", "")
        if not actual:
            raise HTTPException(status_code=404, detail="E2 BoM workbook not yet generated.")
        file_path = engines_dir / "e2" / "output" / Path(actual).name
    elif filename == "distributor_export.xlsx":
        actual = (step_outputs.get("e2") or {}).get("distributor_file", "")
        if not actual:
            raise HTTPException(status_code=404, detail="E2 distributor export not yet generated.")
        file_path = engines_dir / "e2" / "output" / Path(actual).name
    elif filename == "technical_proposal.docx":
        actual = (step_outputs.get("e3") or {}).get("output_file", "")
        if not actual:
            raise HTTPException(status_code=404, detail="E3 technical proposal not yet generated.")
        file_path = engines_dir / "e3" / "output" / Path(actual).name
    elif filename == "submission.pdf":
        actual = (step_outputs.get("e3") or {}).get("pdf_file", "")
        if not actual:
            raise HTTPException(status_code=404, detail="E3 submission PDF not yet generated.")
        file_path = engines_dir / "e3" / "output" / Path(actual).name
    elif filename == "hld_lld.docx":
        actual = (step_outputs.get("e5") or {}).get("output_file", "")
        if not actual:
            raise HTTPException(status_code=404, detail="E5 HLD/LLD document not yet generated.")
        file_path = engines_dir / "e5" / "output" / Path(actual).name
    else:
        raise HTTPException(status_code=404, detail=f"Unknown output file '{filename}'.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk.")

    mime_types = {
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
    }
    mime = mime_types.get(file_path.suffix.lower(), "application/octet-stream")

    return FileResponse(path=str(file_path), media_type=mime, filename=filename)
