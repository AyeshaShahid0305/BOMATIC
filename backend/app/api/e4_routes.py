from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.engines.e4 import run_e4_pipeline

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e4" / "output"

router = APIRouter(prefix="/e4", tags=["e4"])


@router.post("/generate")
async def generate_rfi(
    rfp_session_id: str = Form(""),
    project_name: str = Form("RFI Project"),
    db: Session = Depends(get_db),
):
    session_id: Optional[str] = rfp_session_id.strip() or None
    return run_e4_pipeline(session_id, db)


@router.get("/download/{filename}")
def download_rfi(filename: str):
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
