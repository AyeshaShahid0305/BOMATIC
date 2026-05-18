from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState


def read_e1_data(session_id: str, db: Session) -> dict:
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == session_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline state not found for this session.")

    documents = (
        db.query(Document)
        .filter(Document.opportunity_id == opportunity.id)
        .all()
    )

    rfp_text = "\n\n".join(doc.text_content for doc in documents if doc.text_content)

    # Build a req_id -> compliance status lookup from the matrix (step 10), if available
    matrix_rows: list[dict] = pipeline.step_outputs.get("10", [])
    compliance_by_req_id = {row["req_id"]: row["status"] for row in matrix_rows if "req_id" in row}

    requirements = [
        {
            "text": r.get("text", ""),
            "category": r.get("classification", ""),
            "compliance_status": compliance_by_req_id.get(r.get("id", "")),
        }
        for r in pipeline.step_outputs.get("3", [])
    ]

    legal_traps = [
        f["flag"]
        for f in pipeline.step_outputs.get("4", [])
        if f.get("flag")
    ]

    missing_documents = [
        m["referenced_doc"]
        for m in pipeline.step_outputs.get("2", [])
        if m.get("referenced_doc")
    ]

    project_name = opportunity.project_name or ""
    if not project_name and documents:
        project_name = Path(documents[0].filename).stem

    return {
        "rfp_text": rfp_text,
        "requirements": requirements,
        "legal_traps": legal_traps,
        "missing_documents": missing_documents,
        "project_name": project_name,
    }
