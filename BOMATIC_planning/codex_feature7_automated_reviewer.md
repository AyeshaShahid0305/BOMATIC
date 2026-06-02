# Codex Task: Feature 7 — Automated Reviewer (Pre-Checkpoint Quality Gate)

## Context

BOMATIC is a FastAPI + Next.js + PostgreSQL pre-sales platform. The architecture
specifies a single-pass Sonnet reviewer that fires automatically after each engine
run, before the engineer sees the checkpoint UI. Its job is to catch obvious failures
so engineers don't waste time approving bad output.

This task implements the reviewer for E1 only (Checkpoint 1 and Checkpoint 2).
The same pattern can be extended to E2-E5 later.

**Scope:**
- A new `backend/app/api/reviewer.py` service with two reviewer functions.
- CP1 reviewer fires at the end of `POST /api/e1/{id}/run`.
- CP2 reviewer fires at the end of `POST /api/e1/{id}/checkpoint1/approve`.
- Results stored in `step_outputs["review_cp1"]` and `step_outputs["review_cp2"]`.
- New route `GET /api/e1/{id}/review/{checkpoint}` returns the stored result.
- New route `POST /api/e1/{id}/review/{checkpoint}/rerun` re-triggers the reviewer.
- New `<ReviewBanner>` React component shown at the top of each checkpoint page.
- Approve button is disabled when `errors` list is non-empty.

**AI call pattern (copy exactly from existing engine code):**
```python
import anthropic
client = anthropic.Anthropic(api_key=api_key)
response = client.messages.create(
    model=CLAUDE_MODEL,
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
)
```
`CLAUDE_MODEL` is imported from `app.config`. If `api_key` is empty or the call
fails, fall back to a passed result (warnings only, no errors) — never block the
engineer.

---

## Step 1 — Read these files first (in this order)

Read every file completely before writing any code.

1. `backend/app/config.py`
2. `backend/app/api/e1_router.py`
3. `backend/app/engines/e1/step10_matrix_generator.py`
4. `backend/app/models/pipeline_state.py`
5. `frontend/app/e1/[id]/checkpoint1/page.jsx`
6. `frontend/app/e1/[id]/checkpoint2/page.jsx`
7. `frontend/app/components/DownloadButton.tsx`

---

## Step 2 — Create `backend/app/api/reviewer.py`

Create this file with exactly this content:

```python
"""
Automated reviewer — single-pass Sonnet quality gate.

run_cp1_reviewer(step_outputs, api_key) -> dict
run_cp2_reviewer(step_outputs, api_key) -> dict

Each returns a ReviewResult dict:
{
    "passed": bool,          # True if errors list is empty
    "warnings": list[str],   # Yellow flags — engineer should check but can proceed
    "errors":   list[str],   # Red flags — approve button is disabled until resolved
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
        # Expect a JSON array of strings, e.g. ["Warning one.", "Warning two."]
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
        return []
    except Exception as exc:
        print(f"Reviewer AI call failed ({type(exc).__name__}): {exc}")
        return []


# ---------------------------------------------------------------------------
# CP1 Reviewer — checks steps 1-4 output
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

    # ── Deterministic checks ──────────────────────────────────────────────

    # Error: no files classified at all
    if not files:
        errors.append("No files were classified. Check that uploaded files are readable and in a supported format.")

    # Error: no requirements extracted
    if not reqs:
        errors.append("No requirements were extracted. The RFP may be a blank or unreadable document.")

    # Warning: low-confidence classifications
    low_conf = [f["filename"] for f in files if f.get("confidence", 1.0) < 0.5]
    if low_conf:
        names = ", ".join(low_conf[:3])
        more = f" (+{len(low_conf) - 3} more)" if len(low_conf) > 3 else ""
        warnings.append(f"Low-confidence classification (<50%) on: {names}{more}. Verify these files were correctly identified.")

    # Warning: zero mandatory requirements
    mandatory_count = sum(1 for r in reqs if r.get("classification") == "mandatory")
    if reqs and mandatory_count == 0:
        warnings.append("No mandatory requirements detected. Most RFPs contain mandatory items — check that the correct document was uploaded.")

    # Warning: critical risk flags present
    critical_flags = [f for f in flags if f.get("severity") in ("critical", "high")]
    if critical_flags:
        warnings.append(f"{len(critical_flags)} high/critical risk flag(s) detected. Review before proceeding.")

    # Warning: missing docs with high severity
    high_missing = [d for d in missing if d.get("severity") in ("critical", "high")]
    if high_missing:
        docs = ", ".join(d.get("referenced_doc", "unknown") for d in high_missing[:3])
        warnings.append(f"High-severity missing documents: {docs}. Obtain these before submission.")

    # ── AI qualitative check (only if deterministic passed) ───────────────
    if not errors and reqs:
        sample_reqs = reqs[:10]  # cap to keep prompt short
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
# CP2 Reviewer — checks step 10 compliance matrix output
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

    # ── Deterministic checks ──────────────────────────────────────────────

    # Error: no matrix rows at all
    if not matrix_rows:
        errors.append("Compliance matrix is empty. Re-run Checkpoint 1 approval to generate the matrix.")

    # Error: mandatory requirements with no control mapping (gap_type = orphan)
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

    # Warning: high non-compliance rate
    total = stats.get("total_reqs", 0)
    non_compliant = stats.get("non_compliant", 0)
    if total > 0 and non_compliant / total > 0.3:
        pct = int(non_compliant / total * 100)
        warnings.append(
            f"{pct}% of requirements are Non-Compliant ({non_compliant}/{total}). "
            "Verify these are genuine gaps before submitting."
        )

    # Warning: coverage gaps
    coverage_gaps: list[dict] = gaps.get("coverage_gaps", [])
    if coverage_gaps:
        warnings.append(
            f"{len(coverage_gaps)} framework control(s) have no matching requirement. "
            "Consider whether these controls should be addressed in the proposal."
        )

    # Warning: rows where status is "Compliant" but confidence is low
    low_confidence_compliant = [
        r for r in matrix_rows
        if r.get("status") == "Compliant" and float(r.get("compliance_confidence", 1.0)) < 0.5
    ]
    if low_confidence_compliant:
        warnings.append(
            f"{len(low_confidence_compliant)} requirement(s) marked Compliant with low AI confidence. "
            "Review these rows manually."
        )

    # ── AI qualitative check (only if deterministic passed) ───────────────
    if not errors and matrix_rows:
        # Summarise the matrix for the AI
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
```

---

## Step 3 — Update `backend/app/api/e1_router.py`

Make three targeted changes. Do not rewrite or restructure the file.

**Change 1 — Add import at the top.**

After the existing imports block, add:
```python
from app.api.reviewer import run_cp1_reviewer, run_cp2_reviewer
```

**Change 2 — Call CP1 reviewer at the end of `run_e1_pipeline`.**

Find the block at the end of `run_e1_pipeline` that does the db.commit():
```python
    pipeline.current_step = 4
    opportunity.status = "checkpoint_1_pending"
    db.commit()

    return {
```

Replace it with:
```python
    pipeline.current_step = 4
    opportunity.status = "checkpoint_1_pending"

    # Run automated reviewer before engineer sees Checkpoint 1
    review_result = run_cp1_reviewer(pipeline.step_outputs, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_cp1": review_result}

    db.commit()

    return {
```

**Change 3 — Call CP2 reviewer at the end of `checkpoint1_approve`.**

Find the block at the end of `checkpoint1_approve` that does the db.commit():
```python
    pipeline.current_step = 11
    opportunity.status = "checkpoint_2_pending"
    db.commit()

    return {
```

Replace it with:
```python
    pipeline.current_step = 11
    opportunity.status = "checkpoint_2_pending"

    # Run automated reviewer before engineer sees Checkpoint 2
    review_result = run_cp2_reviewer(pipeline.step_outputs, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_cp2": review_result}

    db.commit()

    return {
```

**Change 4 — Add two new routes at the bottom of `e1_router.py`.**

Add these after the existing `patch_matrix_row` function and after the revision endpoints.

```python
# ---------------------------------------------------------------------------
# Reviewer routes
# ---------------------------------------------------------------------------

@router.get("/{opportunity_id}/review/{checkpoint}")
def get_review_result(
    opportunity_id: str,
    checkpoint: str,
    db: Session = Depends(get_db),
):
    """
    Return the stored review result for a checkpoint.
    checkpoint must be 'cp1' or 'cp2'.
    Returns 404 if the reviewer has not yet run for this checkpoint.
    """
    if checkpoint not in ("cp1", "cp2"):
        raise HTTPException(status_code=400, detail="checkpoint must be 'cp1' or 'cp2'.")

    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    key = f"review_{checkpoint}"
    result = (pipeline.step_outputs or {}).get(key)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Review for {checkpoint} has not run yet.",
        )
    return result


@router.post("/{opportunity_id}/review/{checkpoint}/rerun")
async def rerun_review(
    opportunity_id: str,
    checkpoint: str,
    db: Session = Depends(get_db),
):
    """
    Re-trigger the reviewer for a checkpoint without re-running the full engine.
    Useful after an engineer manually edits the output before approving.
    checkpoint must be 'cp1' or 'cp2'.
    """
    if checkpoint not in ("cp1", "cp2"):
        raise HTTPException(status_code=400, detail="checkpoint must be 'cp1' or 'cp2'.")

    settings = get_settings()
    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    step_outputs = pipeline.step_outputs or {}

    if checkpoint == "cp1":
        if pipeline.current_step < 4:
            raise HTTPException(status_code=409, detail="Steps 1-4 not yet completed.")
        review_result = run_cp1_reviewer(step_outputs, settings.anthropic_api_key)
        key = "review_cp1"
    else:
        if pipeline.current_step < 11:
            raise HTTPException(status_code=409, detail="Checkpoint 1 not yet approved.")
        review_result = run_cp2_reviewer(step_outputs, settings.anthropic_api_key)
        key = "review_cp2"

    pipeline.step_outputs = {**step_outputs, key: review_result}
    db.commit()

    return review_result
```

---

## Step 4 — Create `frontend/app/components/ReviewBanner.tsx`

Create this file:

```tsx
"use client";

import { useEffect, useState } from "react";

type ReviewResult = {
  passed: boolean;
  warnings: string[];
  errors: string[];
  checked_at: string;
};

type ReviewBannerProps = {
  opportunityId: string;
  checkpoint: "cp1" | "cp2";
  /** Called with true when errors=[] (approve button should enable), false otherwise */
  onReady: (canApprove: boolean) => void;
};

export default function ReviewBanner({ opportunityId, checkpoint, onReady }: ReviewBannerProps) {
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);

  async function fetchReview() {
    setLoading(true);
    try {
      const res = await fetch(
        `/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}`
      );
      if (res.status === 404) {
        // Reviewer hasn't run yet — treat as passed with no issues
        onReady(true);
        return;
      }
      if (!res.ok) throw new Error(`${res.status}`);
      const data: ReviewResult = await res.json();
      setReview(data);
      onReady(data.errors.length === 0);
    } catch {
      // On fetch error, don't block the engineer
      onReady(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleRerun() {
    setRerunning(true);
    try {
      const res = await fetch(
        `/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}/rerun`,
        { method: "POST" }
      );
      if (res.ok) {
        const data: ReviewResult = await res.json();
        setReview(data);
        onReady(data.errors.length === 0);
      }
    } catch {
      // Non-blocking
    } finally {
      setRerunning(false);
    }
  }

  useEffect(() => {
    fetchReview();
  }, [opportunityId, checkpoint]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-5 py-4 text-sm text-gray-400 shadow-sm">
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
        </svg>
        Running automated review…
      </div>
    );
  }

  if (!review) return null;

  const hasErrors = review.errors.length > 0;
  const hasWarnings = review.warnings.length > 0;

  if (!hasErrors && !hasWarnings) {
    return (
      <div className="flex items-center justify-between rounded-xl border border-green-200 bg-green-50 px-5 py-4 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-500 text-white text-xs font-bold">✓</span>
          <span className="text-sm font-medium text-green-800">Automated review passed — no issues found.</span>
        </div>
        <button
          onClick={handleRerun}
          disabled={rerunning}
          className="text-xs text-green-600 underline hover:text-green-800 disabled:opacity-50"
        >
          {rerunning ? "Re-running…" : "Re-run"}
        </button>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border shadow-sm ${hasErrors ? "border-red-200 bg-red-50" : "border-yellow-200 bg-yellow-50"}`}>
      <div className="flex items-center justify-between px-5 py-4">
        <div className="flex items-center gap-3">
          <span className={`flex h-6 w-6 items-center justify-center rounded-full text-white text-xs font-bold ${hasErrors ? "bg-red-500" : "bg-yellow-500"}`}>
            {hasErrors ? "!" : "⚠"}
          </span>
          <span className={`text-sm font-semibold ${hasErrors ? "text-red-800" : "text-yellow-800"}`}>
            {hasErrors
              ? `Automated review found ${review.errors.length} issue(s) that must be resolved.`
              : `Automated review passed with ${review.warnings.length} warning(s).`}
          </span>
        </div>
        <button
          onClick={handleRerun}
          disabled={rerunning}
          className={`text-xs underline disabled:opacity-50 ${hasErrors ? "text-red-600 hover:text-red-800" : "text-yellow-600 hover:text-yellow-800"}`}
        >
          {rerunning ? "Re-running…" : "Re-run"}
        </button>
      </div>

      {hasErrors && (
        <div className="border-t border-red-200 px-5 pb-4 pt-3 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-red-600">Must Fix</p>
          <ul className="space-y-1.5">
            {review.errors.map((e, i) => (
              <li key={i} className="flex gap-2 text-sm text-red-700">
                <span className="mt-0.5 shrink-0">•</span>
                <span>{e}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasWarnings && (
        <div className={`border-t px-5 pb-4 pt-3 space-y-2 ${hasErrors ? "border-red-200" : "border-yellow-200"}`}>
          <p className={`text-xs font-semibold uppercase tracking-wide ${hasErrors ? "text-red-500" : "text-yellow-600"}`}>
            Warnings
          </p>
          <ul className="space-y-1.5">
            {review.warnings.map((w, i) => (
              <li key={i} className={`flex gap-2 text-sm ${hasErrors ? "text-red-600" : "text-yellow-700"}`}>
                <span className="mt-0.5 shrink-0">•</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasErrors && (
        <div className="border-t border-red-200 px-5 py-3">
          <p className="text-xs text-red-500">
            Fix the issues above, then click Re-run to clear this block. The Approve button is
            disabled until all errors are resolved.
          </p>
        </div>
      )}
    </div>
  );
}
```

---

## Step 5 — Update checkpoint pages to show ReviewBanner

### 5A. Update `frontend/app/e1/[id]/checkpoint1/page.jsx`

Make three targeted changes.

**Change 1 — Import ReviewBanner.**

Add this import at the top of the file, after the existing React imports:
```js
import ReviewBanner from "@/app/components/ReviewBanner";
```

**Change 2 — Add `reviewBlocked` state variable.**

Find the state declarations block. Add after the existing state lines:
```js
  const [reviewBlocked, setReviewBlocked] = useState(false);
```

**Change 3 — Add ReviewBanner above the first SectionCard, and wire approve button.**

Find the `{/* Section 1 */}` comment in the main content area:
```jsx
        {/* Section 1 */}
        <SectionCard title="Section A — Classified Files">
```

Insert the ReviewBanner immediately before it:
```jsx
        {/* Automated review banner */}
        <ReviewBanner
          opportunityId={id}
          checkpoint="cp1"
          onReady={(canApprove) => setReviewBlocked(!canApprove)}
        />

        {/* Section 1 */}
        <SectionCard title="Section A — Classified Files">
```

Then find the Approve button in the sticky bottom bar:
```jsx
            <button
              onClick={handleApprove}
              disabled={approving || step >= 11}
              ...
            >
```

Add `reviewBlocked` to the disabled condition:
```jsx
            <button
              onClick={handleApprove}
              disabled={approving || step >= 11 || reviewBlocked}
              ...
            >
```

---

### 5B. Update `frontend/app/e1/[id]/checkpoint2/page.jsx`

Same pattern as CP1 — three targeted changes.

**Change 1 — Import ReviewBanner.**
```js
import ReviewBanner from "@/app/components/ReviewBanner";
```

**Change 2 — Add `reviewBlocked` state variable.**
```js
  const [reviewBlocked, setReviewBlocked] = useState(false);
```

**Change 3 — Add ReviewBanner before the Stats summary card, and wire approve button.**

Find the start of the main content area:
```jsx
        {/* Stats bar */}
        <SectionCard title="Summary">
```

Insert immediately before it:
```jsx
        {/* Automated review banner */}
        <ReviewBanner
          opportunityId={id}
          checkpoint="cp2"
          onReady={(canApprove) => setReviewBlocked(!canApprove)}
        />

        {/* Stats bar */}
        <SectionCard title="Summary">
```

Then find the Approve button and add `reviewBlocked` to its disabled condition:
```jsx
              disabled={approving || checkpointComplete || reviewBlocked}
```

---

## Step 6 — Validation steps

Run each check in order. Fix any failure before the next.

### 6A. Backend syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/reviewer.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e1_router.py
```
Expected: no output.

### 6B. Backend import check
```
backend\.venv\Scripts\python.exe -c "
from app.api.reviewer import run_cp1_reviewer, run_cp2_reviewer
from app.api.e1_router import get_review_result, rerun_review
print('all reviewer imports OK')
"
```
Expected: `all reviewer imports OK`

### 6C. Unit test the reviewer with mock data (no API call)

```
backend\.venv\Scripts\python.exe -c "
from app.api.reviewer import run_cp1_reviewer, run_cp2_reviewer

# CP1: empty step_outputs should produce errors
result = run_cp1_reviewer({}, api_key='')
assert result['passed'] == False, 'Expected failed review for empty outputs'
assert len(result['errors']) > 0, 'Expected at least one error'
print('CP1 empty test: PASS')

# CP1: valid outputs should pass
mock_outputs = {
    '1': [{'filename': 'rfp.pdf', 'type': 'rfp', 'confidence': 0.95, 'needs_human_review': False}],
    '2': [],
    '3': [{'id': 'REQ-001', 'text': 'Cisco firewall required', 'classification': 'mandatory', 'confidence': 0.9}],
    '4': [],
}
result = run_cp1_reviewer(mock_outputs, api_key='')
assert result['passed'] == True, f'Expected passed, got errors: {result[\"errors\"]}'
print('CP1 valid test: PASS')

# CP2: empty step_outputs should produce errors
result = run_cp2_reviewer({}, api_key='')
assert result['passed'] == False
assert len(result['errors']) > 0
print('CP2 empty test: PASS')

print('All reviewer unit tests passed.')
"
```
Expected: three `PASS` lines followed by `All reviewer unit tests passed.`

### 6D. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 6E. Frontend build
```
cd frontend && npm run build
```
Expected: zero errors. `ReviewBanner` component appears in build output.

### 6F. Integration test via FastAPI TestClient

```
backend\.venv\Scripts\python.exe -c "
import sys, uuid
sys.path.insert(0, 'backend')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
headers = {'X-API-Key': 'bomatic-dev-key'}
opp_id = f'REVIEW-{uuid.uuid4().hex[:6].upper()}'

# GET review before pipeline run should return 404
r = client.get(f'/api/e1/{opp_id}/review/cp1', headers=headers)
assert r.status_code == 404, f'Expected 404, got {r.status_code}'
print('Pre-run 404: PASS')

# Invalid checkpoint name should return 400
r = client.get(f'/api/e1/{opp_id}/review/cp99', headers=headers)
assert r.status_code == 400, f'Expected 400, got {r.status_code}'
print('Invalid checkpoint 400: PASS')

print('Integration tests passed.')
"
```
Expected: two `PASS` lines.

### 6G. End-to-end manual check (dev server)

Start the backend and `npm run dev`. Log in and open an opportunity that has NOT yet
been run through E1.

1. Upload files and run E1 (`POST /api/e1/{id}/run`).
2. Navigate to `/e1/{id}/checkpoint1`.
3. Verify the `ReviewBanner` appears at the top of the page.
4. If the review passed: banner is green, Approve button is enabled.
5. If errors found: banner is red, Approve button is disabled, "Re-run" link visible.
6. Approve Checkpoint 1, then navigate to `/e1/{id}/checkpoint2`.
7. Verify `ReviewBanner` appears with CP2 review results.

---

## Step 7 — Summary of files changed

| Action   | File path                                              |
|----------|--------------------------------------------------------|
| Created  | `backend/app/api/reviewer.py`                          |
| Modified | `backend/app/api/e1_router.py`                         |
| Created  | `frontend/app/components/ReviewBanner.tsx`             |
| Modified | `frontend/app/e1/[id]/checkpoint1/page.jsx`            |
| Modified | `frontend/app/e1/[id]/checkpoint2/page.jsx`            |

No DB migration needed. No other files modified.

---

## Step 8 — Git commit message

```
feat: add automated reviewer quality gate for E1 checkpoints

Backend:
- app/api/reviewer.py: run_cp1_reviewer and run_cp2_reviewer
  CP1 checks: file classification presence, requirement count,
  low-confidence files, mandatory requirement count, critical risk flags,
  missing docs severity + one Sonnet qualitative pass
  CP2 checks: empty matrix, orphan mandatory requirements, non-compliance
  rate >30%, coverage gaps, low-confidence Compliant rows + one Sonnet pass
  Falls back gracefully (passed=True, warnings only) if API key missing or AI fails
- e1_router.py: reviewer fires at end of run_e1_pipeline (cp1) and
  checkpoint1_approve (cp2); results stored in step_outputs["review_cp1/cp2"]
- GET /api/e1/{id}/review/{checkpoint}: returns stored review result
- POST /api/e1/{id}/review/{checkpoint}/rerun: re-triggers reviewer without
  re-running the full engine

Frontend:
- ReviewBanner.tsx: green/yellow/red banner with error list, warning list,
  Re-run button; calls onReady(canApprove) to gate the Approve button
- checkpoint1/page.jsx: ReviewBanner added above Section A; Approve disabled
  when reviewBlocked=true
- checkpoint2/page.jsx: ReviewBanner added above Stats summary; same gate
```
