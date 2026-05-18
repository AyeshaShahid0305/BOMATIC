from pathlib import Path

from .step1_rfp_extractor import extract_rfp_requirements
from .step1_template_detector import detect_template
from .step2_boq_parser import parse as parse_boq
from .step3_catalog_matcher import match_catalog
from .step4_gap_analyzer import analyze_gaps
from .step5_excel_writer import write_output


def run_e2_pipeline(rfp_text: str, template_path: Path) -> dict:
    rfp_items = extract_rfp_requirements(rfp_text)

    detection = detect_template(template_path)
    boq_items = parse_boq(template_path, detection)  # noqa: F841 — available for future steps

    matches = match_catalog(rfp_items)
    summary = analyze_gaps(matches)
    output_path = write_output(summary, template_path, detection)

    return {
        "output_file": output_path,
        "matched_count": len(summary.matched_items),
        "unmatched_count": len(summary.unmatched_items),
        "low_confidence_count": len(summary.low_confidence_items),
        "subtotal": summary.subtotal,
        "discount_amount": summary.discount_amount,
        "total": summary.total,
        "currency": summary.currency,
    }
