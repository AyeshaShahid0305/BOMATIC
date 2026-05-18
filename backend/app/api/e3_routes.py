from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.engines.e3 import run_e3_pipeline

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e3" / "output"

router = APIRouter(prefix="/e3", tags=["e3"])


@router.post("/generate")
def generate_proposal(
    rfp_session_id: str = Form(...),
    gbb_tier: str = Form("better"),
    db: Session = Depends(get_db),
):
    return run_e3_pipeline(rfp_session_id, db, gbb_tier)


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
