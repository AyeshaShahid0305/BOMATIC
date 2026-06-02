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
