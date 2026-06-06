from typing import Optional

from sqlalchemy.orm import Session

from app.schemas.pipeline import E2PricingArtifact
from .step1_template_selector import select_template
from .step2_e1_data_reader import read_e1_data
from .step2b_e4_data_reader import read_e4_data
from .step2c_e5_data_reader import read_e5_data
from .step3_e2_data_reader import read_e2_data
from .step4_narrative_generator import generate_narratives
from .step5_assembler import assemble_proposal
from .step6_docx_writer import write_proposal
from .step7_pdf_converter import convert_docx_to_pdf
from .step8_gbb_pricing import calculate_gbb


def run_e3_pipeline(
    session_id: str,
    db: Session,
    gbb_tier: str = "better",
    pricing_summary: Optional[E2PricingArtifact] = None,
    allow_placeholders: bool = False,
) -> dict:
    sections = select_template("rfp")
    e1_data = read_e1_data(session_id, db)
    e4_data = read_e4_data(session_id, db)
    e5_data = read_e5_data(session_id, db)

    e1_data["requirements"] = [
        *e1_data.get("requirements", []),
        *e4_data["requirements"],
    ]
    e1_data["rfi_gaps"] = e4_data["gaps"]
    e1_data["design_components"] = e5_data["components"]

    base_price = pricing_summary.total if pricing_summary else 0.0
    gbb_result = calculate_gbb(base_price, gbb_tier)

    e2_data = read_e2_data(pricing_summary) if pricing_summary else {}
    e2_data["design_components"] = e5_data["components"]
    narratives = generate_narratives(e1_data, e2_data, sections, gbb_tier)
    assembled = assemble_proposal(
        sections,
        narratives,
        e1_data,
        e2_data,
        gbb_result,
        allow_placeholders=allow_placeholders,
    )
    output_path = write_proposal(assembled, e1_data["project_name"], gbb_tier)

    # Convert DOCX to PDF (best-effort - None if LibreOffice unavailable)
    pdf_path = convert_docx_to_pdf(output_path, output_path.parent)

    return {
        "output_file": output_path.name,
        "pdf_file": pdf_path.name if pdf_path else None,
        "project_name": e1_data["project_name"],
        "section_count": len(assembled),
        "ai_generated_count": sum(1 for s in assembled if s["ai_generated"]),
        "gbb_tier": gbb_tier,
        "gbb_multiplier": gbb_result.multiplier,
        "total_price": gbb_result.adjusted_price,
        "e4_requirement_count": len(e4_data["requirements"]),
        "e4_gap_count": len(e4_data["gaps"]),
        "e5_component_count": len(e5_data["components"]),
    }
