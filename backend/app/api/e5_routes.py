from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.engines.e5 import run_e5_pipeline

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e5" / "output"

router = APIRouter(prefix="/e5", tags=["e5"])


@router.post("/generate")
async def generate_design(
    rfp_session_id: str = Form(...),
    db: Session = Depends(get_db),
):
    return run_e5_pipeline(rfp_session_id.strip(), db)


@router.get("/download/{filename}")
def download_design(filename: str):
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
