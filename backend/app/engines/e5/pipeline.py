from typing import Optional

from sqlalchemy.orm import Session

from .models import DesignDocument
from .step1_context_reader import read_context
from .step2_hld_generator import generate_hld
from .step3_lld_generator import generate_lld
from .step4_docx_writer import write_design_document


def run_e5_pipeline(session_id: Optional[str], db: Session) -> dict:
    context = read_context(session_id, db)
    hld_sections = generate_hld(context)
    lld_sections = generate_lld(context, hld_sections)

    doc = DesignDocument(
        project_name=context["project_name"],
        hld_sections=hld_sections,
        lld_sections=lld_sections,
        generated_from="e1" if context["has_e1_data"] else "blank",
    )

    output_path = write_design_document(doc)

    return {
        "output_file": output_path.name,
        "project_name": context["project_name"],
        "hld_section_count": len(hld_sections),
        "lld_section_count": len(lld_sections),
        "generated_from": doc.generated_from,
        "total_sections": len(hld_sections) + len(lld_sections),
    }
