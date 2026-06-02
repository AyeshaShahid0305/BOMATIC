"""
Automated reviewer - single-pass Sonnet quality gate.

run_cp1_reviewer(step_outputs, api_key) -> dict
run_cp2_reviewer(step_outputs, api_key) -> dict

Each returns a ReviewResult dict:
{
    "passed": bool,          # True if errors list is empty
    "warnings": list[str],   # Yellow flags - engineer should check but can proceed
    "errors":   list[str],   # Red flags - approve button is disabled until resolved
    "checked_at": str,       # ISO 8601 UTC timestamp
}

Design rules:
- Deterministic code checks run first (fast, no AI).
- If api_key is empty OR the AI call fails, fall back to passed=True with the
  deterministic warnings only. Never block the engineer due to an AI failure.
- One Sonnet call per reviewer, max_tokens=512.
"""

import json
from datetime import datetime, timezone

import anthropic

from app.config import CLAUDE_MODEL


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ai_qualitative_check(prompt: str, api_key: str) -> list[str]:
    """
    Make a single Sonnet call. Returns a list of warning strings.
    Returns [] on any failure (empty key, network error, bad JSON).
    """
    if not api_key:
        return []
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
        return []
    except Exception as exc:
        print(f"Reviewer AI call failed ({type(exc).__name__}): {exc}")
        return []


# ---------------------------------------------------------------------------
# CP1 Reviewer - checks steps 1-4 output
# ---------------------------------------------------------------------------

def run_cp1_reviewer(step_outputs: dict, api_key: str) -> dict:
    """
    Quality gate for Checkpoint 1.
    Checks: classified files (step 1), missing docs (step 2),
            requirements (step 3), risk flags (step 4).
    """
    errors: list[str] = []
    warnings: list[str] = []

    files: list[dict] = step_outputs.get("1", [])
    missing: list[dict] = step_outputs.get("2", [])
    reqs: list[dict] = step_outputs.get("3", [])
    flags: list[dict] = step_outputs.get("4", [])

    if not files:
        errors.append("No files were classified. Check that uploaded files are readable and in a supported format.")

    if not reqs:
        errors.append("No requirements were extracted. The RFP may be a blank or unreadable document.")

    low_conf = [f["filename"] for f in files if f.get("confidence", 1.0) < 0.5]
    if low_conf:
        names = ", ".join(low_conf[:3])
        more = f" (+{len(low_conf) - 3} more)" if len(low_conf) > 3 else ""
        warnings.append(f"Low-confidence classification (<50%) on: {names}{more}. Verify these files were correctly identified.")

    mandatory_count = sum(1 for r in reqs if r.get("classification") == "mandatory")
    if reqs and mandatory_count == 0:
        warnings.append("No mandatory requirements detected. Most RFPs contain mandatory items - check that the correct document was uploaded.")

    critical_flags = [f for f in flags if f.get("severity") in ("critical", "high")]
    if critical_flags:
        warnings.append(f"{len(critical_flags)} high/critical risk flag(s) detected. Review before proceeding.")

    high_missing = [d for d in missing if d.get("severity") in ("critical", "high")]
    if high_missing:
        docs = ", ".join(d.get("referenced_doc", "unknown") for d in high_missing[:3])
        warnings.append(f"High-severity missing documents: {docs}. Obtain these before submission.")

    if not errors and reqs:
        sample_reqs = reqs[:10]
        req_texts = "\n".join(
            f"- [{r.get('classification','?')}] {r.get('text','')[:120]}"
            for r in sample_reqs
        )
        prompt = f"""You are reviewing an automated RFP requirement extraction. Return ONLY a JSON array of warning strings (or an empty array [] if everything looks fine). Do not explain. Do not add prose.

Extracted requirements sample ({len(reqs)} total, showing up to 10):
{req_texts}

Check for: obvious misclassification (e.g. a date labelled as a requirement), duplicate or near-duplicate requirements, requirements that seem unrelated to IT/networking, or any other issue an engineer should know about before proceeding.

Return format: ["Warning one.", "Warning two."] or []"""

        ai_warnings = _ai_qualitative_check(prompt, api_key)
        warnings.extend(ai_warnings)

    return {
        "passed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "checked_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# CP2 Reviewer - checks step 10 compliance matrix output
# ---------------------------------------------------------------------------

def run_cp2_reviewer(step_outputs: dict, api_key: str) -> dict:
    """
    Quality gate for Checkpoint 2.
    Checks: compliance matrix rows (step 10), gaps, stats.
    """
    errors: list[str] = []
    warnings: list[str] = []

    matrix_rows: list[dict] = step_outputs.get("10", [])
    gaps: dict = step_outputs.get("gaps", {})
    stats: dict = step_outputs.get("stats", {})

    if not matrix_rows:
        errors.append("Compliance matrix is empty. Re-run Checkpoint 1 approval to generate the matrix.")

    orphan_mandatory = [
        r for r in matrix_rows
        if r.get("gap_type") == "orphan" and r.get("classification") == "mandatory"
    ]
    if orphan_mandatory:
        ids = ", ".join(r.get("req_id", "?") for r in orphan_mandatory[:5])
        more = f" (+{len(orphan_mandatory) - 5} more)" if len(orphan_mandatory) > 5 else ""
        errors.append(
            f"Mandatory requirements with no framework control mapping: {ids}{more}. "
            "These must be mapped before the matrix can be submitted."
        )

    total = stats.get("total_reqs", 0)
    non_compliant = stats.get("non_compliant", 0)
    if total > 0 and non_compliant / total > 0.3:
        pct = int(non_compliant / total * 100)
        warnings.append(
            f"{pct}% of requirements are Non-Compliant ({non_compliant}/{total}). "
            "Verify these are genuine gaps before submitting."
        )

    coverage_gaps: list[dict] = gaps.get("coverage_gaps", [])
    if coverage_gaps:
        warnings.append(
            f"{len(coverage_gaps)} framework control(s) have no matching requirement. "
            "Consider whether these controls should be addressed in the proposal."
        )

    low_confidence_compliant = [
        r for r in matrix_rows
        if r.get("status") == "Compliant" and float(r.get("compliance_confidence", 1.0)) < 0.5
    ]
    if low_confidence_compliant:
        warnings.append(
            f"{len(low_confidence_compliant)} requirement(s) marked Compliant with low AI confidence. "
            "Review these rows manually."
        )

    if not errors and matrix_rows:
        status_counts = {}
        for r in matrix_rows:
            s = r.get("status", "Unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        orphan_count = len(gaps.get("orphan_requirements", []))
        gap_count = len(coverage_gaps)

        prompt = f"""You are reviewing an automated compliance matrix. Return ONLY a JSON array of warning strings (or [] if everything looks fine). Do not explain. Do not add prose.

Matrix summary:
- Total rows: {len(matrix_rows)}
- Status counts: {json.dumps(status_counts)}
- Orphan requirements (no control): {orphan_count}
- Coverage gaps (no requirement): {gap_count}
- Frameworks used: {list(set(r.get('framework','') for r in matrix_rows if r.get('framework')))}

Check for: unusually high "Compliant" rate (could indicate over-optimistic AI), all requirements mapped to a single framework (could indicate misconfiguration), or any pattern that would concern a compliance engineer reviewing this for the first time.

Return format: ["Warning one.", "Warning two."] or []"""

        ai_warnings = _ai_qualitative_check(prompt, api_key)
        warnings.extend(ai_warnings)

    return {
        "passed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "checked_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# E2 Reviewer - checks BoM generation output
# ---------------------------------------------------------------------------

def run_e2_reviewer(e2_data: dict, api_key: str) -> dict:
    """
    Quality gate for E2 (Bill of Materials).
    Checks: matched_count, unmatched_count, low_confidence_count, totals.
    """
    errors: list[str] = []
    warnings: list[str] = []

    matched = e2_data.get("matched_count", 0)
    unmatched = e2_data.get("unmatched_count", 0)
    low_conf = e2_data.get("low_confidence_count", 0)
    total = e2_data.get("total", 0)
    vendor_list = e2_data.get("vendor_list", [])
    req_count = e2_data.get("requirements_baseline_count", 0)

    # Error: nothing was matched at all
    if matched == 0 and unmatched == 0:
        errors.append(
            "No items were processed. The BoQ template may be empty or in an "
            "unsupported format."
        )

    # Error: total is zero with matched items (pricing data missing)
    if matched > 0 and total == 0:
        errors.append(
            "Matched items found but total price is zero. "
            "Catalog pricing data may be missing - check the catalog."
        )

    # Warning: high unmatched rate
    total_items = matched + unmatched
    if total_items > 0 and unmatched / total_items > 0.3:
        pct = int(unmatched / total_items * 100)
        warnings.append(
            f"{pct}% of items ({unmatched}/{total_items}) could not be matched to the "
            "catalog. Review NEEDS REVIEW rows in the BoM workbook before approving."
        )

    # Warning: low-confidence matches
    if low_conf > 0:
        warnings.append(
            f"{low_conf} item(s) matched with low confidence. "
            "Verify SKU selections in the BoM workbook."
        )

    # Warning: no vendors identified from E1
    if not vendor_list:
        warnings.append(
            "No vendor list was passed from E1. Catalog matching used all vendors - "
            "results may be less accurate."
        )

    # Warning: EoX hits
    eox_warnings = e2_data.get("eox_warnings", [])
    eos_hits = [w for w in eox_warnings if w.get("is_end_of_sale")]
    eol_hits = [w for w in eox_warnings if w.get("is_end_of_support")]

    if eol_hits:
        skus = ", ".join(w["sku"] for w in eol_hits[:3])
        more = f" (+{len(eol_hits) - 3} more)" if len(eol_hits) > 3 else ""
        errors.append(
            f"End-of-Life SKUs in BoM: {skus}{more}. These products are no longer "
            "supported - replace with recommended alternatives before submitting."
        )
    elif eos_hits:
        skus = ", ".join(w["sku"] for w in eos_hits[:3])
        more = f" (+{len(eos_hits) - 3} more)" if len(eos_hits) > 3 else ""
        warnings.append(
            f"End-of-Sale SKUs in BoM: {skus}{more}. These products can no longer "
            "be ordered - verify availability or use replacements."
        )

    # AI qualitative check
    if not errors:
        prompt = f"""You are reviewing an automated Bill of Materials generation result.
Return ONLY a JSON array of warning strings (or [] if everything looks fine).
Do not explain or add prose.

BoM summary:
- Matched items: {matched}
- Unmatched items: {unmatched}
- Low confidence matches: {low_conf}
- Total price: {e2_data.get('currency', 'USD')} {total:,.2f}
- Vendors: {vendor_list}
- Requirements processed: {req_count}

Check for: suspiciously low total price for the number of items, vendor mix that
seems inconsistent (e.g. Cisco and Fortinet mixed without explanation), or any
pattern an engineer should know about before approving.

Return format: ["Warning one.", "Warning two."] or []"""
        warnings.extend(_ai_qualitative_check(prompt, api_key))

    return {
        "passed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "checked_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# E3 Reviewer - checks proposal generation output
# ---------------------------------------------------------------------------

def run_e3_reviewer(e3_data: dict, api_key: str) -> dict:
    """
    Quality gate for E3 (Technical Proposal).
    Checks: section_count, output_file presence.
    """
    errors: list[str] = []
    warnings: list[str] = []

    section_count = e3_data.get("section_count", 0)
    output_file = e3_data.get("output_file", "")
    pdf_file = e3_data.get("pdf_file", "")
    project_name = e3_data.get("project_name", "")

    # Error: no output file
    if not output_file:
        errors.append(
            "No proposal document was generated. Re-run E3 generation."
        )

    # Error: zero sections
    if section_count == 0:
        errors.append(
            "The proposal has zero sections. The template selector may have failed."
        )

    # Warning: very few sections
    if 0 < section_count < 5:
        warnings.append(
            f"Only {section_count} section(s) generated. A typical proposal has 8-15 "
            "sections - verify the template was applied correctly."
        )

    # Warning: no PDF
    if output_file and not pdf_file:
        warnings.append(
            "PDF conversion was skipped (LibreOffice not found). "
            "Install LibreOffice to generate submission.pdf."
        )

    # Warning: generic project name
    if project_name in ("", "Untitled", "RFP Project"):
        warnings.append(
            "Project name is generic or missing. Update the opportunity's project name "
            "before submitting the proposal."
        )

    # AI qualitative check
    if not errors:
        prompt = f"""You are reviewing an automated technical proposal generation result.
Return ONLY a JSON array of warning strings (or [] if everything looks fine).
Do not explain or add prose.

Proposal summary:
- Project name: {project_name}
- Sections generated: {section_count}
- DOCX produced: {'yes' if output_file else 'no'}
- PDF produced: {'yes' if pdf_file else 'no'}

Check for: anything an engineer should verify before sending this proposal to a client.

Return format: ["Warning one.", "Warning two."] or []"""
        warnings.extend(_ai_qualitative_check(prompt, api_key))

    return {
        "passed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "checked_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# E4 Reviewer - checks RFI questionnaire output
# ---------------------------------------------------------------------------

def run_e4_reviewer(e4_data: dict, api_key: str) -> dict:
    """
    Quality gate for E4 (RFI Questionnaire).
    Checks: total_questions, categories, must_have_count.
    """
    errors: list[str] = []
    warnings: list[str] = []

    total = e4_data.get("total_questions", 0)
    categories = e4_data.get("categories", [])
    must_have = e4_data.get("must_have_count", 0)
    nice_to_have = e4_data.get("nice_to_have_count", 0)
    output_file = e4_data.get("output_file", "")

    # Error: no questions generated
    if total == 0:
        errors.append(
            "No questions were generated. The E4 engine may have failed - re-run generation."
        )

    # Error: no output file
    if not output_file:
        errors.append(
            "No questionnaire file was produced. Re-run E4 generation."
        )

    # Warning: no must-have questions
    if total > 0 and must_have == 0:
        warnings.append(
            "No must-have questions were generated. Every RFI should have at least "
            "some mandatory items - verify the question template."
        )

    # Warning: very few questions
    if 0 < total < 10:
        warnings.append(
            f"Only {total} question(s) generated. A typical RFI questionnaire has "
            "20-60 questions."
        )

    # Warning: no categories
    if not categories:
        warnings.append(
            "No question categories were identified. The questionnaire may lack structure."
        )

    # AI qualitative check
    if not errors:
        prompt = f"""You are reviewing an automated RFI questionnaire generation result.
Return ONLY a JSON array of warning strings (or [] if everything looks fine).
Do not explain or add prose.

Questionnaire summary:
- Total questions: {total}
- Must-have: {must_have}
- Nice-to-have: {nice_to_have}
- Categories: {categories}

Check for: imbalanced must-have vs nice-to-have ratio, missing categories typical
for network infrastructure RFIs, or any issue the engineer should know before
sending this questionnaire to the client.

Return format: ["Warning one.", "Warning two."] or []"""
        warnings.extend(_ai_qualitative_check(prompt, api_key))

    return {
        "passed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "checked_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# E5 Reviewer - checks HLD/LLD design output
# ---------------------------------------------------------------------------

def run_e5_reviewer(e5_data: dict, api_key: str) -> dict:
    """
    Quality gate for E5 (HLD/LLD Design).
    Checks: total_sections, output_file presence.
    """
    errors: list[str] = []
    warnings: list[str] = []

    total_sections = e5_data.get("total_sections", 0)
    output_file = e5_data.get("output_file", "")
    project_name = e5_data.get("project_name", "")

    # Error: no output file
    if not output_file:
        errors.append(
            "No design document was generated. Re-run E5 generation."
        )

    # Error: zero sections
    if total_sections == 0:
        errors.append(
            "The design document has zero sections. E5 generation may have failed."
        )

    # Warning: very few sections
    if 0 < total_sections < 8:
        warnings.append(
            f"Only {total_sections} section(s) generated. A typical HLD/LLD document "
            "has 12-21 sections - verify the template was applied correctly."
        )

    # Warning: generic project name
    if project_name in ("", "Untitled", "RFI Project"):
        warnings.append(
            "Project name is generic or missing. Update before submitting the design."
        )

    # AI qualitative check
    if not errors:
        prompt = f"""You are reviewing an automated HLD/LLD design document generation result.
Return ONLY a JSON array of warning strings (or [] if everything looks fine).
Do not explain or add prose.

Design summary:
- Project name: {project_name}
- Total sections: {total_sections}
- Document produced: {'yes' if output_file else 'no'}

Check for: anything an engineer should verify before approving this design document
and passing the component list to the BoM engine.

Return format: ["Warning one.", "Warning two."] or []"""
        warnings.extend(_ai_qualitative_check(prompt, api_key))

    return {
        "passed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "checked_at": _now_iso(),
    }
