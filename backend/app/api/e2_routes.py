import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.engines.e2 import run_e2_pipeline
from app.models.document import Document
from app.models.opportunity import Opportunity

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e2" / "output"

router = APIRouter(prefix="/e2", tags=["e2"])


@router.post("/analyze")
async def analyze_boq(
    rfp_session_id: str = Form(...),
    boq_template: UploadFile = File(...),
    db: Session = Depends(get_db),
):
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

        result = run_e2_pipeline(rfp_text, template_path)
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
