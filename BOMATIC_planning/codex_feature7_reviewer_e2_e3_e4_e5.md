# Codex Task: F7 Reviewer Extension — E2, E3, E4, E5

## Context

BOMATIC already has an automated reviewer for E1 checkpoints (CP1 and CP2) in
`backend/app/api/reviewer.py`. The pattern is: deterministic code checks first,
one Sonnet call for qualitative assessment, result stored in `step_outputs`, read
by a `<ReviewBanner>` component on each checkpoint page.

This task extends the reviewer to E2, E3, E4, E5 using the exact same pattern.

**What gets added:**
1. Four new reviewer functions in `reviewer.py`:
   `run_e2_reviewer`, `run_e3_reviewer`, `run_e4_reviewer`, `run_e5_reviewer`
2. Each fires at the end of its engine's generate endpoint (stored in step_outputs).
3. New GET + POST rerun routes in each engine's route file.
4. `<ReviewBanner>` added to each checkpoint page.
5. Approve button disabled when reviewer has errors.

**Data available per engine (from step_outputs):**
- E2: matched_count, unmatched_count, low_confidence_count, subtotal, total,
  currency, vendor_list, requirements_baseline_count
- E3: project_name, section_count, output_file, pdf_file
- E4: project_name, total_questions, categories, must_have_count,
  nice_to_have_count, output_file
- E5: project_name, total_sections, output_file

**Reviewer storage keys:** `step_outputs["review_e2"]`, `["review_e3"]`,
`["review_e4"]`, `["review_e5"]`

**Fallback rule (same as E1):** if api_key is empty or AI call fails, return
`passed=True` with deterministic warnings only. Never block engineer due to AI failure.

---

## Step 1 — Read these files first

1. `backend/app/api/reviewer.py` — full file, understand the pattern
2. `backend/app/api/e2_routes.py`
3. `backend/app/api/e3_routes.py`
4. `backend/app/api/e4_routes.py`
5. `backend/app/api/e5_routes.py`
6. `frontend/app/components/ReviewBanner.tsx`
7. `frontend/app/e2/[id]/page.tsx`
8. `frontend/app/e3/[id]/review/page.tsx`
9. `frontend/app/e4/[id]/page.tsx`
10. `frontend/app/e5/[id]/page.tsx`

---

## Step 2 — Add four reviewer functions to `backend/app/api/reviewer.py`

Append these four functions to the bottom of `reviewer.py`. Do not modify any
existing function.

```python
# ---------------------------------------------------------------------------
# E2 Reviewer — checks BoM generation output
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
            "Catalog pricing data may be missing — check the catalog."
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
            "No vendor list was passed from E1. Catalog matching used all vendors — "
            "results may be less accurate."
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
# E3 Reviewer — checks proposal generation output
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
            f"Only {section_count} section(s) generated. A typical proposal has 8–15 "
            "sections — verify the template was applied correctly."
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
# E4 Reviewer — checks RFI questionnaire output
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
            "No questions were generated. The E4 engine may have failed — re-run generation."
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
            "some mandatory items — verify the question template."
        )

    # Warning: very few questions
    if 0 < total < 10:
        warnings.append(
            f"Only {total} question(s) generated. A typical RFI questionnaire has "
            "20–60 questions."
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
# E5 Reviewer — checks HLD/LLD design output
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
            "has 12–21 sections — verify the template was applied correctly."
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
```

---

## Step 3 — Wire reviewer into each engine's generate endpoint

### 3A. `backend/app/api/e2_routes.py`

**Add import** at the top:
```python
from app.api.reviewer import run_e2_reviewer
from app.config import get_settings
```

**Fire reviewer** at the end of the `analyze_boq` function, immediately before
`db.commit()`. Find:
```python
            flag_modified(pipeline_state, 'step_outputs')
            db.commit()
```

Replace with:
```python
            # Run automated reviewer before engineer sees E2 checkpoint
            settings = get_settings()
            review_result = run_e2_reviewer(outputs['e2'], settings.anthropic_api_key)
            outputs['review_e2'] = review_result
            pipeline_state.step_outputs = outputs
            flag_modified(pipeline_state, 'step_outputs')
            db.commit()
```

**Add review routes** at the bottom of `e2_routes.py`:
```python
@router.get("/{opportunity_id}/review")
def get_e2_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the stored E2 review result."""
    _, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)
    result = (pipeline.step_outputs or {}).get("review_e2")
    if not result:
        raise HTTPException(status_code=404, detail="E2 review has not run yet.")
    return result


@router.post("/{opportunity_id}/review/rerun")
def rerun_e2_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Re-trigger the E2 reviewer without re-running the full engine."""
    from app.config import get_settings
    settings = get_settings()
    opportunity, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)
    e2_data = (pipeline.step_outputs or {}).get("e2")
    if not e2_data:
        raise HTTPException(status_code=404, detail="E2 has not been run yet.")
    review_result = run_e2_reviewer(e2_data, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_e2": review_result}
    flag_modified(pipeline, "step_outputs")
    db.commit()
    return review_result
```

---

### 3B. `backend/app/api/e3_routes.py`

**Add import:**
```python
from app.api.reviewer import run_e3_reviewer
from app.config import get_settings
```

**Fire reviewer** inside `generate_proposal`, immediately before `db.commit()`.
Find the block ending with:
```python
            flag_modified(pipeline_state, 'step_outputs')
            db.commit()
```

Replace with:
```python
            # Run automated reviewer before engineer sees E3 checkpoint
            settings = get_settings()
            review_result = run_e3_reviewer(outputs['e3'], settings.anthropic_api_key)
            outputs['review_e3'] = review_result
            pipeline_state.step_outputs = outputs
            flag_modified(pipeline_state, 'step_outputs')
            db.commit()
```

**Add review routes** at the bottom:
```python
@router.get("/{opportunity_id}/review")
def get_e3_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the stored E3 review result."""
    _, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)
    result = (pipeline.step_outputs or {}).get("review_e3")
    if not result:
        raise HTTPException(status_code=404, detail="E3 review has not run yet.")
    return result


@router.post("/{opportunity_id}/review/rerun")
def rerun_e3_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Re-trigger the E3 reviewer without re-running the full engine."""
    from app.config import get_settings
    settings = get_settings()
    _, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)
    e3_data = (pipeline.step_outputs or {}).get("e3")
    if not e3_data:
        raise HTTPException(status_code=404, detail="E3 has not been run yet.")
    review_result = run_e3_reviewer(e3_data, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_e3": review_result}
    flag_modified(pipeline, "step_outputs")
    db.commit()
    return review_result
```

---

### 3C. `backend/app/api/e4_routes.py`

**Add import:**
```python
from app.api.reviewer import run_e4_reviewer
from app.config import get_settings
```

**Fire reviewer** inside `generate_rfi`, immediately before `db.commit()`:
```python
                # Run automated reviewer before engineer sees E4 checkpoint
                settings = get_settings()
                review_result = run_e4_reviewer(outputs['e4'], settings.anthropic_api_key)
                outputs['review_e4'] = review_result
                pipeline_state.step_outputs = outputs
                flag_modified(pipeline_state, 'step_outputs')
                db.commit()
```

Note: in `e4_routes.py` the DB commit is inside the `if pipeline_state:` block.
Place the reviewer call and the `flag_modified` call immediately before the
existing `db.commit()` inside that block.

**Add review routes** at the bottom:
```python
@router.get("/{opportunity_id}/review")
def get_e4_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the stored E4 review result."""
    _, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)
    result = (pipeline.step_outputs or {}).get("review_e4")
    if not result:
        raise HTTPException(status_code=404, detail="E4 review has not run yet.")
    return result


@router.post("/{opportunity_id}/review/rerun")
def rerun_e4_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Re-trigger the E4 reviewer without re-running the full engine."""
    from app.config import get_settings
    settings = get_settings()
    _, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)
    e4_data = (pipeline.step_outputs or {}).get("e4")
    if not e4_data:
        raise HTTPException(status_code=404, detail="E4 has not been run yet.")
    review_result = run_e4_reviewer(e4_data, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_e4": review_result}
    flag_modified(pipeline, "step_outputs")
    db.commit()
    return review_result
```

---

### 3D. `backend/app/api/e5_routes.py`

**Add import:**
```python
from app.api.reviewer import run_e5_reviewer
from app.config import get_settings
```

**Fire reviewer** inside `generate_design`, immediately before `db.commit()`:
```python
                # Run automated reviewer before engineer sees E5 checkpoint
                settings = get_settings()
                review_result = run_e5_reviewer(outputs['e5'], settings.anthropic_api_key)
                outputs['review_e5'] = review_result
                pipeline_state.step_outputs = outputs
                flag_modified(pipeline_state, 'step_outputs')
                db.commit()
```

**Add review routes** at the bottom:
```python
@router.get("/{opportunity_id}/review")
def get_e5_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Return the stored E5 review result."""
    _, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)
    result = (pipeline.step_outputs or {}).get("review_e5")
    if not result:
        raise HTTPException(status_code=404, detail="E5 review has not run yet.")
    return result


@router.post("/{opportunity_id}/review/rerun")
def rerun_e5_review(opportunity_id: str, db: Session = Depends(get_db)):
    """Re-trigger the E5 reviewer without re-running the full engine."""
    from app.config import get_settings
    settings = get_settings()
    _, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)
    e5_data = (pipeline.step_outputs or {}).get("e5")
    if not e5_data:
        raise HTTPException(status_code=404, detail="E5 has not been run yet.")
    review_result = run_e5_reviewer(e5_data, settings.anthropic_api_key)
    pipeline.step_outputs = {**pipeline.step_outputs, "review_e5": review_result}
    flag_modified(pipeline, "step_outputs")
    db.commit()
    return review_result
```

---

## Step 4 — Frontend: Add ReviewBanner to each checkpoint page

The `<ReviewBanner>` component at `frontend/app/components/ReviewBanner.tsx`
already exists. It accepts `opportunityId`, `checkpoint`, and `onReady` props.
Currently `checkpoint` is typed as `"cp1" | "cp2"`. Update the type to accept
the new engine keys.

### 4A. Update `ReviewBanner.tsx` type

Find:
```tsx
  checkpoint: "cp1" | "cp2";
```

Replace with:
```tsx
  checkpoint: "cp1" | "cp2" | "e2" | "e3" | "e4" | "e5";
```

Also update the fetch URL inside ReviewBanner. Currently it calls:
```tsx
`/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}`
```

Replace the fetch URL logic so it uses the right path per engine:

Find the `fetchReview` function's fetch call:
```tsx
      const res = await fetch(
        `/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}`
      );
```

Replace with:
```tsx
      const engine = ["cp1", "cp2"].includes(checkpoint) ? "e1" : checkpoint;
      const reviewPath = ["cp1", "cp2"].includes(checkpoint)
        ? `/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}`
        : `/api/${engine}/${encodeURIComponent(opportunityId)}/review`;
      const res = await fetch(reviewPath);
```

Also update the rerun fetch URL in `handleRerun`:

Find:
```tsx
      const res = await fetch(
        `/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}/rerun`,
        { method: "POST" }
      );
```

Replace with:
```tsx
      const rerunPath = ["cp1", "cp2"].includes(checkpoint)
        ? `/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}/rerun`
        : `/api/${checkpoint}/${encodeURIComponent(opportunityId)}/review/rerun`;
      const res = await fetch(rerunPath, { method: "POST" });
```

---

### 4B. Update `frontend/app/e2/[id]/page.tsx`

**Add import** at the top:
```tsx
import ReviewBanner from "@/app/components/ReviewBanner";
```

**Add `reviewBlocked` state** after the existing state declarations:
```tsx
  const [reviewBlocked, setReviewBlocked] = useState(false);
```

**Add ReviewBanner** at the top of the data section, immediately before the stats
grid. Find:
```tsx
            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
```

Insert before it:
```tsx
            <ReviewBanner
              opportunityId={id}
              checkpoint="e2"
              onReady={(canApprove) => setReviewBlocked(!canApprove)}
            />
```

**Wire approve button**: add `reviewBlocked` to the disabled condition:
```tsx
              disabled={approving || approved || reviewBlocked}
```

---

### 4C. Update `frontend/app/e3/[id]/review/page.tsx`

**Add import:**
```tsx
import ReviewBanner from "@/app/components/ReviewBanner";
```

**Add `reviewBlocked` state** alongside the existing `approving`/`approved` state:
```tsx
  const [reviewBlocked, setReviewBlocked] = useState(false);
```

**Add ReviewBanner** before the downloads card. Find the opening of the E3 complete
section:
```tsx
        {e3Complete && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Downloads
```

Insert immediately before it:
```tsx
        {e3Complete && (
          <ReviewBanner
            opportunityId={id}
            checkpoint="e3"
            onReady={(canApprove) => setReviewBlocked(!canApprove)}
          />
        )}
```

**Wire approve button**: in the approve button rendered in the proposal summary card,
add `reviewBlocked` to disabled:
```tsx
                  disabled={approving || reviewBlocked}
```

---

### 4D. Update `frontend/app/e4/[id]/page.tsx`

**Add import:**
```tsx
import ReviewBanner from "@/app/components/ReviewBanner";
```

**Add `reviewBlocked` state:**
```tsx
  const [reviewBlocked, setReviewBlocked] = useState(false);
```

**Add ReviewBanner** before the stats grid. Find:
```tsx
            <div className="grid grid-cols-3 gap-4">
```

Insert before it:
```tsx
            <ReviewBanner
              opportunityId={id}
              checkpoint="e4"
              onReady={(canApprove) => setReviewBlocked(!canApprove)}
            />
```

**Wire approve button**: add `reviewBlocked` to disabled:
```tsx
              disabled={approving || approved || reviewBlocked}
```

---

### 4E. Update `frontend/app/e5/[id]/page.tsx`

**Add import:**
```tsx
import ReviewBanner from "@/app/components/ReviewBanner";
```

**Add `reviewBlocked` state:**
```tsx
  const [reviewBlocked, setReviewBlocked] = useState(false);
```

**Add ReviewBanner** before the downloads card. Find:
```tsx
        {e5Complete && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Downloads
```

Insert before it:
```tsx
        {e5Complete && (
          <ReviewBanner
            opportunityId={id}
            checkpoint="e5"
            onReady={(canApprove) => setReviewBlocked(!canApprove)}
          />
        )}
```

**Wire approve button**: add `reviewBlocked` to the approve button's disabled:
```tsx
                  disabled={approving || reviewBlocked}
```

---

## Step 5 — Validation steps

### 5A. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/reviewer.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e2_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e3_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e4_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e5_routes.py
```
Expected: no output.

### 5B. Import check
```
backend\.venv\Scripts\python.exe -c "
from app.api.reviewer import (
    run_e2_reviewer, run_e3_reviewer, run_e4_reviewer, run_e5_reviewer
)
print('reviewer imports OK')
from app.api.e2_routes import get_e2_review, rerun_e2_review
from app.api.e3_routes import get_e3_review, rerun_e3_review
from app.api.e4_routes import get_e4_review, rerun_e4_review
from app.api.e5_routes import get_e5_review, rerun_e5_review
print('route imports OK')
"
```
Expected: two `OK` lines.

### 5C. Unit test all four reviewers with mock data
```
backend\.venv\Scripts\python.exe -c "
from app.api.reviewer import run_e2_reviewer, run_e3_reviewer, run_e4_reviewer, run_e5_reviewer

# E2: empty data -> error
r = run_e2_reviewer({}, api_key='')
assert not r['passed'], 'E2 empty should fail'
assert r['errors'], 'E2 empty should have errors'
print('E2 empty: PASS')

# E2: valid data -> pass
r = run_e2_reviewer({'matched_count': 10, 'unmatched_count': 1,
    'low_confidence_count': 0, 'total': 50000, 'currency': 'USD',
    'vendor_list': ['Cisco'], 'requirements_baseline_count': 8}, api_key='')
assert r['passed'], f'E2 valid failed: {r[\"errors\"]}'
print('E2 valid: PASS')

# E3: missing output_file -> error
r = run_e3_reviewer({'section_count': 10, 'output_file': '', 'pdf_file': '', 'project_name': 'Test'}, api_key='')
assert not r['passed']
print('E3 no file: PASS')

# E3: valid -> pass
r = run_e3_reviewer({'section_count': 12, 'output_file': 'test.docx', 'pdf_file': 'test.pdf', 'project_name': 'Campus Network'}, api_key='')
assert r['passed'], f'E3 valid failed: {r[\"errors\"]}'
print('E3 valid: PASS')

# E4: zero questions -> error
r = run_e4_reviewer({'total_questions': 0, 'categories': [], 'must_have_count': 0, 'nice_to_have_count': 0, 'output_file': ''}, api_key='')
assert not r['passed']
print('E4 empty: PASS')

# E4: valid -> pass
r = run_e4_reviewer({'total_questions': 30, 'categories': ['Network', 'Security'], 'must_have_count': 20, 'nice_to_have_count': 10, 'output_file': 'rfi.xlsx'}, api_key='')
assert r['passed'], f'E4 valid failed: {r[\"errors\"]}'
print('E4 valid: PASS')

# E5: no output -> error
r = run_e5_reviewer({'total_sections': 0, 'output_file': '', 'project_name': ''}, api_key='')
assert not r['passed']
print('E5 empty: PASS')

# E5: valid -> pass
r = run_e5_reviewer({'total_sections': 15, 'output_file': 'design.docx', 'project_name': 'HQ Upgrade'}, api_key='')
assert r['passed'], f'E5 valid failed: {r[\"errors\"]}'
print('E5 valid: PASS')

print('All reviewer unit tests passed.')
"
```
Expected: 8 PASS lines then `All reviewer unit tests passed.`

### 5D. Route smoke test
```
backend\.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, 'backend')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
headers = {'X-API-Key': 'bomatic-dev-key'}

for engine in ['e2', 'e3', 'e4', 'e5']:
    r = client.get(f'/api/{engine}/NONEXISTENT/review', headers=headers)
    assert r.status_code == 404, f'{engine} review: expected 404 got {r.status_code}'
    print(f'{engine} review 404: PASS')
    r = client.post(f'/api/{engine}/NONEXISTENT/review/rerun', headers=headers)
    assert r.status_code == 404, f'{engine} rerun: expected 404 got {r.status_code}'
    print(f'{engine} rerun 404: PASS')

print('All route checks passed.')
"
```
Expected: 8 PASS lines then `All route checks passed.`

### 5E. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 5F. Frontend build
```
cd frontend && npm run build
```
Expected: zero errors.

---

## Step 6 — Summary of files changed

| Action   | File path                                      |
|----------|------------------------------------------------|
| Modified | `backend/app/api/reviewer.py`                  |
| Modified | `backend/app/api/e2_routes.py`                 |
| Modified | `backend/app/api/e3_routes.py`                 |
| Modified | `backend/app/api/e4_routes.py`                 |
| Modified | `backend/app/api/e5_routes.py`                 |
| Modified | `frontend/app/components/ReviewBanner.tsx`     |
| Modified | `frontend/app/e2/[id]/page.tsx`                |
| Modified | `frontend/app/e3/[id]/review/page.tsx`         |
| Modified | `frontend/app/e4/[id]/page.tsx`                |
| Modified | `frontend/app/e5/[id]/page.tsx`                |

No DB migration. No new dependencies.

---

## Step 7 — Git commit message

```
feat: extend automated reviewer to E2, E3, E4, E5

reviewer.py: add run_e2/e3/e4/e5_reviewer functions
  E2: checks matched/unmatched counts, zero total with matches, high
    unmatched rate (>30%), low confidence items, missing vendor list
  E3: checks output_file presence, section count, PDF availability,
    generic project name
  E4: checks question count, output file, must-have count, categories
  E5: checks output file, section count, generic project name
  All: one Sonnet qualitative pass; fallback to passed=True on AI failure

e2/e3/e4/e5_routes.py: fire reviewer at end of generate endpoint;
  store in step_outputs["review_e{n}"]; add GET /{id}/review and
  POST /{id}/review/rerun routes

ReviewBanner.tsx: extend checkpoint type to include e2/e3/e4/e5;
  update fetch URL logic to use correct API path per engine

e2/e3/e4/e5 checkpoint pages: import ReviewBanner, add reviewBlocked
  state, render banner above data, gate approve button on reviewBlocked
```
