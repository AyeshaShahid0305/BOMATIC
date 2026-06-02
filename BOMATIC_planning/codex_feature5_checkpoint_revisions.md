# Codex Task: Feature 5 — Human Checkpoint Revision Loops

## Context

BOMATIC is a FastAPI + Next.js + PostgreSQL pre-sales platform. Two E1 checkpoint
pages already exist:

- `frontend/app/e1/[id]/checkpoint1/page.jsx` — reviews steps 1-4 output. Has a
  "Request Revision" button and modal UI, but `handleRevisionSubmit` only shows a
  static message: "Revision re-run is not yet available." The backend endpoint does
  not exist.

- `frontend/app/e1/[id]/checkpoint2/page.jsx` — reviews the compliance matrix. Has
  an Approve button but no revision mechanism at all.

This task wires up real revision loops for both checkpoints:
- Max 3 revisions per checkpoint. The 4th attempt returns HTTP 409.
- CP1 revision re-runs steps 3-4 (requirements extraction + legal trap detection).
- CP2 revision re-runs steps 8-11 (sector detection, framework selection, compliance
  matrix generation, TP section linking) — same steps run by checkpoint1/approve.
- Revision counts are stored in `PipelineState.step_outputs["revision_counts"]` as a
  dict (no DB migration needed — it's just another key in the existing JSONB column).
- The frontend shows a counter "Revision X of 3" and disables the revision button
  when the max is reached.

Do not touch any other engine's files. Only E1 checkpoint revision is in scope.

---

## Step 1 — Read these files first (in this order)

Read every file completely before writing any code.

1. `backend/app/api/e1_router.py`
2. `backend/app/models/pipeline_state.py`
3. `backend/app/models/opportunity.py`
4. `backend/app/db.py`
5. `backend/app/config.py`
6. `frontend/app/e1/[id]/checkpoint1/page.jsx`
7. `frontend/app/e1/[id]/checkpoint2/page.jsx`

---

## Step 2 — Backend changes: add two revision endpoints to `e1_router.py`

Add both functions at the bottom of `backend/app/api/e1_router.py`, after the existing
`patch_matrix_row` function. Do not modify any existing function.

No new imports are needed — all required imports already exist in `e1_router.py`.

---

### 2A. Revision helper

Add this private helper function before the two route functions:

```python
def _get_revision_count(pipeline: PipelineState, checkpoint: str) -> int:
    """Return the current revision count for a checkpoint key ('cp1' or 'cp2')."""
    counts = (pipeline.step_outputs or {}).get("revision_counts", {})
    return counts.get(checkpoint, 0)


def _increment_revision_count(pipeline: PipelineState, checkpoint: str) -> int:
    """
    Increment the revision count for the given checkpoint in step_outputs.
    Returns the NEW count after incrementing.
    Assigns a new dict to step_outputs so SQLAlchemy detects the JSONB change.
    """
    outputs = dict(pipeline.step_outputs or {})
    counts = dict(outputs.get("revision_counts", {}))
    counts[checkpoint] = counts.get(checkpoint, 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = outputs
    return counts[checkpoint]
```

---

### 2B. CP1 revision endpoint

```python
class RevisionRequest(BaseModel):
    engineer_notes: str = ""


@router.post("/{opportunity_id}/checkpoint1/revise")
async def checkpoint1_revise(
    opportunity_id: str,
    body: RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Re-run Steps 3-4 (requirements extraction + legal trap detection) and update
    step_outputs. Max 3 revisions. Returns 409 on the 4th attempt.

    The engineer_notes are stored in step_outputs["revision_notes"]["cp1"] for
    audit purposes but do not alter the deterministic step logic.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 4:
        raise HTTPException(
            status_code=409,
            detail="Steps 1-4 not yet completed. Run the pipeline first.",
        )
    if pipeline.current_step >= 11:
        raise HTTPException(
            status_code=409,
            detail="Checkpoint 1 already approved. Revisions are no longer possible.",
        )

    current_count = _get_revision_count(pipeline, "cp1")
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for Checkpoint 1. Edit output files manually before approving.",
        )

    # Read texts from Document records
    documents = db.query(Document).filter(Document.opportunity_id == opportunity.id).all()
    texts: dict[str, str] = {
        doc.filename: doc.text_content
        for doc in documents
        if doc.text_content
    }
    if not texts:
        raise HTTPException(
            status_code=400,
            detail="No extracted text found. Re-upload the RFP package.",
        )

    # Re-run steps 3 and 4
    reqs = extract_requirements(texts, opportunity_id=opportunity_id)
    flags = detect_legal_traps(texts)

    requirements_payload = [dataclasses.asdict(r) for r in reqs]
    flags_payload = [dataclasses.asdict(f) for f in flags]

    # Increment revision count, store notes, update step outputs
    new_count = _increment_revision_count(pipeline, "cp1")

    outputs = dict(pipeline.step_outputs)

    # Store revision notes for audit trail
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"cp1_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes

    # Overwrite steps 3 and 4 with fresh results
    outputs["3"] = requirements_payload
    outputs["4"] = flags_payload

    # Rebuild the e1 handoff with updated requirements and flags
    e1_existing = outputs.get("e1", {})
    outputs["e1"] = _build_e1_output(
        texts=texts,
        requirements=requirements_payload,
        risk_flags=flags_payload,
        sector=e1_existing.get("sector", ""),
        frameworks_selected=e1_existing.get("frameworks_selected", []),
    )

    pipeline.step_outputs = outputs
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "requirements_count": len(requirements_payload),
        "flags_count": len(flags_payload),
        "step_outputs": {
            "3": requirements_payload,
            "4": flags_payload,
        },
    }
```

---

### 2C. CP2 revision endpoint

```python
@router.post("/{opportunity_id}/checkpoint2/revise")
async def checkpoint2_revise(
    opportunity_id: str,
    body: RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Re-run Steps 8-11 (sector detection, framework selection, compliance matrix
    generation, TP section linking) and update step_outputs.
    Max 3 revisions. Returns 409 on the 4th attempt.
    """
    MAX_REVISIONS = 3
    settings = get_settings()

    opportunity, pipeline = _get_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=409,
            detail="Checkpoint 1 not yet approved. Complete Checkpoint 1 first.",
        )
    if pipeline.current_step >= 12:
        raise HTTPException(
            status_code=409,
            detail="Checkpoint 2 already approved. Revisions are no longer possible.",
        )

    current_count = _get_revision_count(pipeline, "cp2")
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for Checkpoint 2. Edit output files manually before approving.",
        )

    requirements: list[dict] = (pipeline.step_outputs or {}).get("3", [])
    if not requirements:
        raise HTTPException(
            status_code=400,
            detail="No requirements found in pipeline state. Re-run and approve Checkpoint 1 first.",
        )

    # Re-run steps 8-11 (same logic as checkpoint1_approve)
    documents = db.query(Document).filter(Document.opportunity_id == opportunity.id).all()
    texts: dict[str, str] = {
        doc.filename: doc.text_content
        for doc in documents
        if doc.text_content
    }

    client_name = opportunity.client_name or ""

    # Step 8
    sector_result = detect_sector(client_name, texts)

    # Step 9
    related_standards: list[str] = []
    for req in requirements:
        related_standards.extend(req.get("related_standards", []))
    frameworks = select_frameworks(sector_result["sector"], related_standards)

    # Step 10 (AI call — offloaded to threadpool)
    matrix_result = await asyncio.get_running_loop().run_in_executor(
        None,
        functools.partial(
            generate_compliance_matrix,
            requirements=requirements,
            frameworks=frameworks,
            api_key=settings.anthropic_api_key,
            data_dir=_DATA_DIR,
        ),
    )

    # Step 11
    link_tp_sections(matrix_result["matrix_rows"])

    # Increment revision count and store notes
    new_count = _increment_revision_count(pipeline, "cp2")

    outputs = dict(pipeline.step_outputs)

    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"cp2_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes

    outputs["8"] = sector_result
    outputs["9"] = frameworks
    outputs["10"] = matrix_result["matrix_rows"]
    outputs["gaps"] = matrix_result["gaps"]
    outputs["stats"] = matrix_result["stats"]

    # Rebuild e1 handoff with updated sector and frameworks
    e1_existing = outputs.get("e1", {})
    outputs["e1"] = _build_e1_output(
        texts=texts,
        requirements=e1_existing.get("requirements_baseline") or requirements,
        risk_flags=e1_existing.get("risk_flags") or outputs.get("4", []),
        sector=sector_result["sector"],
        frameworks_selected=frameworks,
    )

    pipeline.step_outputs = outputs
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "matrix_row_count": len(matrix_result["matrix_rows"]),
        "stats": matrix_result["stats"],
    }
```

---

## Step 3 — Frontend changes

### 3A. Update `frontend/app/e1/[id]/checkpoint1/page.jsx`

Make three targeted changes. Do not rewrite the file — only modify the parts listed.

**Change 1 — Add revision state variables.**

Find the block that declares component state:
```js
  const [toast, setToast] = useState(null);
```

Add these two lines immediately after it:
```js
  const [revisionCount, setRevisionCount] = useState(0);
  const MAX_REVISIONS = 3;
```

**Change 2 — Read revision count from pipeline state on load.**

Find the `useEffect` that fetches state:
```js
  useEffect(() => {
    fetch(`/api/e1/${id}/state`)
      .then(r => r.ok ? r.json() : r.json().then(b => Promise.reject(b.detail ?? "Failed to load state")))
      .then(setState)
      .catch(err => setLoadError(typeof err === "string" ? err : "Failed to load pipeline state."));
  }, [id]);
```

Replace it with:
```js
  useEffect(() => {
    fetch(`/api/e1/${id}/state`)
      .then(r => r.ok ? r.json() : r.json().then(b => Promise.reject(b.detail ?? "Failed to load state")))
      .then(data => {
        setState(data);
        const counts = data?.step_outputs?.revision_counts ?? {};
        setRevisionCount(counts.cp1 ?? 0);
      })
      .catch(err => setLoadError(typeof err === "string" ? err : "Failed to load pipeline state."));
  }, [id]);
```

**Change 3 — Wire `handleRevisionSubmit` to the backend.**

Find this function and replace it entirely:
```js
  function handleRevisionSubmit() {
    setShowModal(false);
    setToast("Revision re-run is not yet available. Please contact support.");
  }
```

Replace with:
```js
  async function handleRevisionSubmit(notes) {
    setRevisionSubmitting(true);
    try {
      const res = await fetch(`/api/e1/${id}/checkpoint1/revise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engineer_notes: notes }),
      });

      if (res.status === 409) {
        const body = await res.json();
        setShowModal(false);
        setToast(body.detail ?? "Maximum revisions reached.");
        return;
      }
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail ?? `Server error ${res.status}`);
      }

      const data = await res.json();
      setRevisionCount(data.revision_number);

      // Refresh the full pipeline state so the requirements/flags sections update
      const stateRes = await fetch(`/api/e1/${id}/state`);
      if (stateRes.ok) setState(await stateRes.json());

      setShowModal(false);
      setToast(`Revision ${data.revision_number} of ${MAX_REVISIONS} complete. Results updated.`);
    } catch (err) {
      setShowModal(false);
      setToast(`Revision failed: ${err.message}`);
    } finally {
      setRevisionSubmitting(false);
    }
  }
```

**Change 4 — Show revision counter and disable button at max.**

Find the "Request Revision" button in the sticky bottom bar:
```jsx
            <button
              onClick={() => setShowModal(true)}
              disabled={step >= 11}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Request Revision
            </button>
```

Replace with:
```jsx
            <div className="flex flex-col items-end gap-1">
              {revisionCount > 0 && (
                <span className="text-xs text-gray-400">
                  Revision {revisionCount} of {MAX_REVISIONS} used
                </span>
              )}
              <button
                onClick={() => setShowModal(true)}
                disabled={step >= 11 || revisionCount >= MAX_REVISIONS}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {revisionCount >= MAX_REVISIONS ? "Max Revisions Reached" : "Request Revision"}
              </button>
            </div>
```

---

### 3B. Update `frontend/app/e1/[id]/checkpoint2/page.jsx`

Make four targeted changes. Do not rewrite the file.

**Change 1 — Add revision state variables.**

Find:
```js
  const [toast, setToast] = useState(null);
```

Add these immediately after:
```js
  const [revisionCount, setRevisionCount] = useState(0);
  const [revisionSubmitting, setRevisionSubmitting] = useState(false);
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const MAX_REVISIONS = 3;
```

**Change 2 — Read revision count when matrix loads.**

Find the `.then(data => {` block inside the matrix fetch `useEffect`:
```js
      .then(data => {
        setRows(data.matrix_rows ?? []);
        setGaps(data.gaps ?? {});
        setStats(data.stats ?? {});
        setLoading(false);
      })
```

This fetch is for the matrix endpoint which doesn't return revision_counts. After the
`setLoading(false)` line, add a second fetch to read the pipeline state:

Replace the block with:
```js
      .then(data => {
        setRows(data.matrix_rows ?? []);
        setGaps(data.gaps ?? {});
        setStats(data.stats ?? {});
        setLoading(false);
        // Read revision count from pipeline state
        return fetch(`/api/e1/${id}/state`);
      })
      .then(r => r.ok ? r.json() : null)
      .then(stateData => {
        if (stateData) {
          const counts = stateData?.step_outputs?.revision_counts ?? {};
          setRevisionCount(counts.cp2 ?? 0);
        }
      })
```

**Change 3 — Add `handleRevisionSubmit` function.**

Add this function inside the component, after the existing `handleApprove` function:

```js
  async function handleRevisionSubmit(notes) {
    setRevisionSubmitting(true);
    try {
      const res = await fetch(`/api/e1/${id}/checkpoint2/revise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engineer_notes: notes }),
      });

      if (res.status === 409) {
        const body = await res.json();
        setShowRevisionModal(false);
        setToast({ message: body.detail ?? "Maximum revisions reached.", downloadUrl: null });
        return;
      }
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail ?? `Server error ${res.status}`);
      }

      const data = await res.json();
      setRevisionCount(data.revision_number);

      // Refresh the matrix with new results
      const matrixRes = await fetch(`/api/e1/${id}/matrix`);
      if (matrixRes.ok) {
        const matrixData = await matrixRes.json();
        setRows(matrixData.matrix_rows ?? []);
        setGaps(matrixData.gaps ?? {});
        setStats(matrixData.stats ?? {});
      }

      setShowRevisionModal(false);
      setToast({
        message: `Revision ${data.revision_number} of ${MAX_REVISIONS} complete. Matrix updated.`,
        downloadUrl: null,
      });
    } catch (err) {
      setShowRevisionModal(false);
      setToast({ message: `Revision failed: ${err.message}`, downloadUrl: null });
    } finally {
      setRevisionSubmitting(false);
    }
  }
```

**Change 4 — Add revision button to the sticky bottom bar.**

Find the sticky bottom bar's button area:
```jsx
          <button
            onClick={handleApprove}
            disabled={approving || checkpointComplete}
            className="flex items-center gap-2 rounded-lg bg-green-600 px-5 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {approving && <Spinner small />}
            {checkpointComplete ? "Approved" : approving ? "Generating…" : "Approve & Generate Excel"}
          </button>
```

Replace it with the button group (revision + approve side by side):
```jsx
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-end gap-1">
              {revisionCount > 0 && (
                <span className="text-xs text-gray-400">
                  Revision {revisionCount} of {MAX_REVISIONS} used
                </span>
              )}
              <button
                onClick={() => setShowRevisionModal(true)}
                disabled={checkpointComplete || revisionCount >= MAX_REVISIONS}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {revisionCount >= MAX_REVISIONS ? "Max Revisions Reached" : "Request Revision"}
              </button>
            </div>
            <button
              onClick={handleApprove}
              disabled={approving || checkpointComplete}
              className="flex items-center gap-2 rounded-lg bg-green-600 px-5 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {approving && <Spinner small />}
              {checkpointComplete ? "Approved" : approving ? "Generating…" : "Approve & Generate Excel"}
            </button>
          </div>
```

**Change 5 — Add `RevisionModal` component and render it.**

The `checkpoint1/page.jsx` already has a `RevisionModal` component. Copy the same
component into `checkpoint2/page.jsx`. Add it at the top of the file, before the
`export default` function, as a local component:

```jsx
function RevisionModal({ onClose, onSubmit, submitting }) {
  const [notes, setNotes] = useState("");
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
        <h3 className="mb-1 text-base font-semibold text-gray-800">Request Revision</h3>
        <p className="mb-4 text-sm text-gray-500">
          Describe what needs to be corrected. The compliance matrix will be regenerated.
        </p>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={5}
          placeholder="e.g. Control mapping for REQ-005 is incorrect. SAMA CSF should be prioritized over ISO 27001 for this sector."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <div className="mt-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onSubmit(notes)}
            disabled={!notes.trim() || submitting}
            className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Submit Revision Request"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

Then render it in the `return` block of `Checkpoint2Page`, just before the closing
`</div>` of the outermost container (same position as in checkpoint1):

```jsx
      {showRevisionModal && (
        <RevisionModal
          onClose={() => setShowRevisionModal(false)}
          onSubmit={handleRevisionSubmit}
          submitting={revisionSubmitting}
        />
      )}
```

Also ensure `useState` is imported at the top of the file. The existing imports line
already includes it — no change needed if it's there.

---

## Step 4 — Validation steps

Run each check in order. Fix any failure before the next.

### 4A. Backend syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e1_router.py
```
Expected: no output (no errors).

### 4B. Backend import check
```
backend\.venv\Scripts\python.exe -c "
from app.api.e1_router import checkpoint1_revise, checkpoint2_revise
print('revision endpoints import OK')
"
```
Expected: `revision endpoints import OK`

### 4C. TypeScript / JSX check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors. (JSX files are checked if tsconfig includes them.)

### 4D. Curl tests — start backend on port 8000

**Test 1 — CP1 revise before steps 1-4 are run. Should return 409.**
```
curl -s -o /dev/null -w "%{http_code}" -X POST \
  http://localhost:8000/api/e1/NONEXISTENT-OPP/checkpoint1/revise \
  -H "X-API-Key: bomatic-dev-key" \
  -H "Content-Type: application/json" \
  -d "{\"engineer_notes\": \"test\"}"
```
Expected: `404` (opportunity not found)

**Test 2 — CP1 revise on a valid completed opportunity. Should return 200.**

Substitute `<OPP_ID>` with an opportunity that has completed steps 1-4
(current_step >= 4, current_step < 11).

```
curl -s -X POST \
  http://localhost:8000/api/e1/<OPP_ID>/checkpoint1/revise \
  -H "X-API-Key: bomatic-dev-key" \
  -H "Content-Type: application/json" \
  -d "{\"engineer_notes\": \"Test revision notes\"}" | python -m json.tool
```
Expected: JSON with `revision_number: 1`, `revisions_remaining: 2`, `requirements_count`
and `flags_count` as integers.

**Test 3 — Run 3 CP1 revisions then attempt a 4th. Should return 409.**
```
for /L %i in (1,1,3) do curl -s -o /dev/null -X POST \
  http://localhost:8000/api/e1/<OPP_ID>/checkpoint1/revise \
  -H "X-API-Key: bomatic-dev-key" \
  -H "Content-Type: application/json" \
  -d "{\"engineer_notes\": \"revision %i\"}"

curl -s -o /dev/null -w "%{http_code}" -X POST \
  http://localhost:8000/api/e1/<OPP_ID>/checkpoint1/revise \
  -H "X-API-Key: bomatic-dev-key" \
  -H "Content-Type: application/json" \
  -d "{\"engineer_notes\": \"fourth attempt\"}"
```
Expected: `409`

**Test 4 — Verify revision_counts persisted in pipeline state.**
```
curl -s http://localhost:8000/api/e1/<OPP_ID>/state \
  -H "X-API-Key: bomatic-dev-key" | python -m json.tool
```
Expected: `step_outputs.revision_counts.cp1` equals the total revision count run.

**Test 5 — CP2 revise on an opportunity at step 11.**
Substitute `<OPP_ID_CP2>` with an opportunity where current_step == 11.
```
curl -s -X POST \
  http://localhost:8000/api/e1/<OPP_ID_CP2>/checkpoint2/revise \
  -H "X-API-Key: bomatic-dev-key" \
  -H "Content-Type: application/json" \
  -d "{\"engineer_notes\": \"Re-run matrix with updated frameworks\"}" | python -m json.tool
```
Expected: JSON with `revision_number: 1`, `revisions_remaining: 2`, `matrix_row_count`
as integer, `stats` as dict.

### 4E. Frontend build check
```
cd frontend && npm run build
```
Expected: zero errors.

### 4F. Manual UI check (dev server)

Start `npm run dev`. Log in and open an opportunity that has completed steps 1-4.
Navigate to `/e1/{id}/checkpoint1`.

Verify:
- "Request Revision" button is enabled.
- Clicking it opens the modal.
- Submitting the modal calls the backend and shows "Revision 1 of 3 complete" toast.
- The requirements and flags sections refresh with new data.
- After 3 revisions, the button shows "Max Revisions Reached" and is disabled.

---

## Step 5 — Summary of files changed

| Action   | File path                                         |
|----------|---------------------------------------------------|
| Modified | `backend/app/api/e1_router.py`                    |
| Modified | `frontend/app/e1/[id]/checkpoint1/page.jsx`       |
| Modified | `frontend/app/e1/[id]/checkpoint2/page.jsx`       |

No other files should be modified. No DB migration is needed — revision counts
are stored in the existing `step_outputs` JSONB column.

---

## Step 6 — Git commit message

```
feat: wire E1 checkpoint revision loops with max-3 enforcement

Backend (e1_router.py):
- POST /api/e1/{id}/checkpoint1/revise — re-runs steps 3-4 (requirements
  extraction + legal trap detection); stores engineer notes in revision_notes;
  returns 409 after 3 revisions
- POST /api/e1/{id}/checkpoint2/revise — re-runs steps 8-11 (sector,
  frameworks, compliance matrix, TP links); same revision limit and audit trail
- _get_revision_count / _increment_revision_count helpers write to
  step_outputs["revision_counts"] (no migration needed)

Frontend:
- checkpoint1/page.jsx: handleRevisionSubmit now calls backend; shows
  "Revision X of 3 used" counter; disables button at max
- checkpoint2/page.jsx: adds RevisionModal, revision state, handleRevisionSubmit,
  revision counter badge, and revision button alongside Approve button
```
