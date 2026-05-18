import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.engines.e2.step1_rfp_extractor import extract_rfp_requirements
from app.engines.e2.step3_catalog_matcher import match_catalog
from app.engines.e2.step4_gap_analyzer import analyze_gaps
from app.engines.e3 import run_e3_pipeline
from app.models.document import Document
from app.models.opportunity import Opportunity

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

    pricing_summary = None

    if boq_template is not None:
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

    return run_e3_pipeline(rfp_session_id, db, gbb_tier, pricing_summary)


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
