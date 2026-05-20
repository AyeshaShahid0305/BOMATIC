import os
import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.config import get_settings
from app.models.opportunity import Opportunity
from app.models.document import Document
from app.models.pipeline_state import PipelineState

router = APIRouter(prefix="/rfp", tags=["rfp"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".dwg", ".msg", ".doc"}


def _get_file_format(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return ext.lstrip(".") if ext else "unknown"


@router.post("/packages", status_code=status.HTTP_201_CREATED)
async def upload_rfp_package(
    files: list[UploadFile] = File(...),
    opportunity_id: Optional[str] = Form(None),
    client_name: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
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

    # Use provided opportunity_id or generate one
    opp_id_str = opportunity_id or f"OPP-{uuid.uuid4().hex[:8].upper()}"

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

    # Persist opportunity
    opportunity = Opportunity(
        opportunity_id=opp_id_str,
        client_name=client_name,
        project_name=project_name,
        status="uploaded",
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
    }


@router.get("/packages/{opportunity_id}")
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
        "status": opportunity.status,
        "pipeline_step": pipeline.current_step if pipeline else 0,
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
