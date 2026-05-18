from sqlalchemy.orm import Session

from .step1_template_selector import select_template
from .step2_e1_data_reader import read_e1_data
from .step4_narrative_generator import generate_narratives
from .step5_assembler import assemble_proposal
from .step6_docx_writer import write_proposal
from .step8_gbb_pricing import calculate_gbb


def run_e3_pipeline(
    session_id: str,
    db: Session,
    gbb_tier: str = "better",
) -> dict:
    sections = select_template("rfp")
    e1_data = read_e1_data(session_id, db)
    gbb_result = calculate_gbb(0, gbb_tier)

    narratives = generate_narratives(e1_data, {}, sections, gbb_tier)
    assembled = assemble_proposal(sections, narratives, e1_data, {}, gbb_result)
    output_path = write_proposal(assembled, e1_data["project_name"], gbb_tier)

    return {
        "output_file": output_path.name,
        "project_name": e1_data["project_name"],
        "section_count": len(assembled),
        "ai_generated_count": sum(1 for s in assembled if s["ai_generated"]),
        "gbb_tier": gbb_tier,
        "gbb_multiplier": gbb_result.multiplier,
    }
