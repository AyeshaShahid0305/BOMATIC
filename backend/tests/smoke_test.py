import sys, os
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
os.chdir(__import__('pathlib').Path(__file__).parent.parent)

from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from app.db import SessionLocal

# ── E2 steps (no DB needed) ──
from app.engines.e2.step1_rfp_extractor import extract_rfp_requirements
from app.engines.e2.step3_catalog_matcher import match_catalog
from app.engines.e2.step4_gap_analyzer import analyze_gaps
from app.engines.e2.step5_excel_writer import write_output
from app.engines.e2.step1_template_detector import detect_template
from app.engines.e2.step2_boq_parser import parse as parse_boq

rfp_text = Path("tests/fixtures/sample_rfp.txt").read_text()
boq_path = Path("tests/fixtures/sample_boq.xlsx")

print("=== E2 SMOKE TEST ===")
items = extract_rfp_requirements(rfp_text)
print(f"Step1: {len(items)} RFP line items extracted")
for i in items[:3]:
    print(f"  - {i.description[:60]} | qty={i.quantity} | cat={i.category}")

matches = match_catalog(items)
print(f"Step3: {len(matches)} catalog matches")

summary = analyze_gaps(matches)
print(f"Step4: matched={len(summary.matched_items)}, unmatched={len(summary.unmatched_items)}, low_conf={len(summary.low_confidence_items)}")
print(f"       subtotal={summary.subtotal:.2f}, total={summary.total:.2f} {summary.currency}")

detection = detect_template(str(boq_path))
boq_items = parse_boq(str(boq_path), detection)
out = write_output(summary, str(boq_path), detection)
print(f"Step5: Excel written -> {out}")

print()
print("=== E3 SMOKE TEST ===")
from app.engines.e3.step1_template_selector import select_template
from app.engines.e3.step4_narrative_generator import generate_narratives
from app.engines.e3.step5_assembler import assemble_proposal
from app.engines.e3.step6_docx_writer import write_proposal
from app.engines.e3.step8_gbb_pricing import calculate_gbb
from app.engines.e3.step3_e2_data_reader import read_e2_data

e1_data = {
    "project_name": "Network Infrastructure Upgrade - Riyadh HQ",
    "rfp_text": rfp_text,
    "requirements": [{"text": i.description, "category": i.category, "compliance_status": None} for i in items],
    "legal_traps": ["unlimited liability clause", "90-day payment terms", "5% per week penalty"],
    "missing_documents": [],
}

sections = select_template("rfp")
e2_data = read_e2_data(summary)
gbb_result = calculate_gbb(summary.total, "better")
print(f"Step8: GBB better -> {gbb_result.adjusted_price:.2f} USD")

narratives = generate_narratives(e1_data, e2_data, sections, "better")
ai_done = sum(1 for v in narratives.values() if "[Section content" not in v)
print(f"Step4: {ai_done} AI narratives generated out of {len(narratives)} sections")

assembled = assemble_proposal(sections, narratives, e1_data, e2_data, gbb_result)
out_doc = write_proposal(assembled, e1_data["project_name"], "better")
print(f"Step6: DOCX written -> {out_doc}")

print()
print("Smoke test complete")
