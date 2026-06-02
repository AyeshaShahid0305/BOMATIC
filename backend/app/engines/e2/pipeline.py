from pathlib import Path

from app.schemas.pipeline import E1Output

from .step1_rfp_extractor import extract_rfp_requirements
from .step1_template_detector import detect_template
from .step2_boq_parser import parse as parse_boq
from .step3_catalog_matcher import match_catalog
from .step4_gap_analyzer import analyze_gaps
from .step5_excel_writer import write_output, write_distributor_export
from .models import RFPLineItem


def _items_from_e1_output(e1_output: E1Output) -> list[RFPLineItem]:
    items: list[RFPLineItem] = []
    for req in e1_output.requirements_baseline:
        description = str(req.get("text") or req.get("description") or "").strip()
        if not description:
            continue
        items.append(
            RFPLineItem(
                description=description,
                quantity=None,
                unit="items",
                category=str(req.get("category") or "hardware"),
                raw_text=description,
                confidence=float(req.get("confidence") or 0.8),
            )
        )
    return items


def run_e2_pipeline(
    rfp_text: str,
    template_path: Path,
    e1_output: E1Output | None = None,
) -> dict:
    rfp_items = _items_from_e1_output(e1_output) if e1_output else extract_rfp_requirements(rfp_text)

    detection = detect_template(template_path)
    boq_items = parse_boq(template_path, detection)

    matches = match_catalog(rfp_items, vendor_list=e1_output.vendor_list if e1_output else None)
    summary = analyze_gaps(matches)
    output_path = write_output(summary, template_path, detection)
    distributor_path = write_distributor_export(summary, template_path)

    return {
        "output_file": output_path,
        "distributor_file": distributor_path.name,
        "vendor_list": e1_output.vendor_list if e1_output else [],
        "requirements_baseline_count": len(e1_output.requirements_baseline) if e1_output else 0,
        "matched_count": len(summary.matched_items),
        "unmatched_count": len(summary.unmatched_items),
        "low_confidence_count": len(summary.low_confidence_items),
        "subtotal": summary.subtotal,
        "discount_amount": summary.discount_amount,
        "total": summary.total,
        "currency": summary.currency,
        "boq_items": boq_items,
    }
