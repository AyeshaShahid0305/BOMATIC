from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState


def read_context(session_id: str | None, db: Session) -> dict:
    if not session_id:
        return {
            "project_name": "",
            "rfp_text": "",
            "requirements": [],
            "missing_documents": [],
            "legal_traps": [],
            "has_e1_data": False,
        }

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

    requirements = [
        {"text": r.get("text", ""), "category": r.get("classification", "")}
        for r in pipeline.step_outputs.get("3", [])
    ]

    missing_documents = [
        m["referenced_doc"]
        for m in pipeline.step_outputs.get("2", [])
        if m.get("referenced_doc")
    ]

    legal_traps = [
        f["flag"]
        for f in pipeline.step_outputs.get("4", [])
        if f.get("flag")
    ]

    project_name = opportunity.project_name or ""
    if not project_name and documents:
        project_name = Path(documents[0].filename).stem

    return {
        "project_name": project_name,
        "rfp_text": rfp_text,
        "requirements": requirements,
        "missing_documents": missing_documents,
        "legal_traps": legal_traps,
        "has_e1_data": True,
    }
