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
from app.models.pipeline_state import PipelineState
from sqlalchemy.orm.attributes import flag_modified

_OUTPUT_DIR = Path(__file__).parent.parent / "engines" / "e2" / "output"

router = APIRouter(prefix="/e2", tags=["e2"])


@router.post("/analyze")
async def analyze_boq(
    rfp_session_id: str = Form(default=""),
    boq_template: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    pipeline_state = None

    if rfp_session_id.strip():
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

        pipeline_state = (
            db.query(PipelineState)
            .filter(PipelineState.opportunity_id == opportunity.id)
            .first()
        )

        rfp_texts = [doc.text_content for doc in documents if doc.text_content]
        if not rfp_texts:
            raise HTTPException(
                status_code=400,
                detail="No RFP text found for this session. Run E1 analysis first.",
            )

        rfp_text = "\n\n".join(rfp_texts)
    else:
        rfp_text = ""

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        template_name = Path(boq_template.filename or "template.xlsx").name
        template_path = tmp_dir / template_name
        template_path.write_bytes(await boq_template.read())

        result = run_e2_pipeline(rfp_text, template_path)

        if pipeline_state:
            outputs = dict(pipeline_state.step_outputs or {})
            outputs['e2'] = {
                'matched_items': result.get('matched_items', []),
                'subtotal': result.get('subtotal', 0),
                'total_price': result.get('total_price', 0),
                'output_file': Path(result['output_file']).name,
            }
            pipeline_state.step_outputs = outputs
            flag_modified(pipeline_state, 'step_outputs')
            db.commit()

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
