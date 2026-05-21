from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.engines.e4 import run_e4_pipeline
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from sqlalchemy.orm.attributes import flag_modified

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e4" / "output"

router = APIRouter(prefix="/e4", tags=["e4"])


@router.post('/generate')
async def generate_rfi(
    rfp_session_id: str = Form(''),
    project_name: str = Form('RFI Project'),
    db: Session = Depends(get_db),
):
    session_id: Optional[str] = rfp_session_id.strip() or None
    result = run_e4_pipeline(session_id, db)
    if session_id:
        opportunity = (
            db.query(Opportunity)
            .filter(Opportunity.opportunity_id == session_id)
            .first()
        )
        if opportunity:
            pipeline_state = (
                db.query(PipelineState)
                .filter(PipelineState.opportunity_id == opportunity.id)
                .first()
            )
            if pipeline_state:
                outputs = dict(pipeline_state.step_outputs or {})
                outputs['e4'] = {
                    'project_name': result.get('project_name', ''),
                    'total_questions': result.get('total_questions', 0),
                    'categories': result.get('categories', []),
                    'must_have_count': result.get('must_have_count', 0),
                    'nice_to_have_count': result.get('nice_to_have_count', 0),
                    'output_file': result.get('output_file', ''),
                }
                pipeline_state.step_outputs = outputs
                flag_modified(pipeline_state, 'step_outputs')
                db.commit()
    return result


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
