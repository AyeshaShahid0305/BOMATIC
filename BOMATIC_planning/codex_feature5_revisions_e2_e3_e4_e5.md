# Codex Task: F5 Revision Loops for E2, E3, E4, E5

## Context

BOMATIC already has revision loops for E1 checkpoints (CP1 and CP2) in
`backend/app/api/e1_router.py`. The pattern: a `POST /{id}/checkpoint/revise`
endpoint records engineer notes and increments a revision counter stored in
`step_outputs["revision_counts"]`. Max 3 revisions — 4th attempt returns 409.
The frontend shows a counter badge and disables the button at max.

This task extends the same pattern to E2, E3, E4, and E5.

**Key difference from E1:** E1 revision endpoints re-run specific pipeline steps
server-side. E2–E5 revisions record the request but do NOT re-run automatically —
the engine needs fresh inputs (new BoQ file for E2, or re-submission via the
generator page). After a revision is recorded, the frontend shows a message
directing the engineer back to the generator page to re-run.

**Revision counter keys:**
- E2: `step_outputs["revision_counts"]["e2"]`
- E3: `step_outputs["revision_counts"]["e3"]`
- E4: `step_outputs["revision_counts"]["e4"]`
- E5: `step_outputs["revision_counts"]["e5"]`

**Generator page links (for post-revision message):**
- E2: `/e2?session_id={opportunity_id}`
- E3: `/e3?session_id={opportunity_id}`
- E4: `/e4?session_id={opportunity_id}` (or the E4 standalone generator)
- E5: `/e5?session_id={opportunity_id}`

---

## Step 1 — Read these files first

1. `backend/app/api/e1_router.py` — lines around `_get_revision_count`,
   `_increment_revision_count`, `RevisionRequest`, `checkpoint1_revise`
   (lines 494–600 approximately)
2. `backend/app/api/e2_routes.py`
3. `backend/app/api/e3_routes.py`
4. `backend/app/api/e4_routes.py`
5. `backend/app/api/e5_routes.py`
6. `frontend/app/e2/[id]/page.tsx`
7. `frontend/app/e3/[id]/review/page.tsx`
8. `frontend/app/e4/[id]/page.tsx`
9. `frontend/app/e5/[id]/page.tsx`
10. `frontend/app/e1/[id]/checkpoint1/page.jsx` — RevisionModal component

---

## Step 2 — Backend: add revision endpoints to each engine route file

Each engine gets:
- Two private helper functions (`_get_revision_count_{n}`, `_increment_revision_count_{n}`)
- One `RevisionRequest` Pydantic model (if not already defined in that file)
- One `POST /{opportunity_id}/checkpoint/revise` route

The `RevisionRequest` model is the same for all engines:
```python
class RevisionRequest(BaseModel):
    engineer_notes: str = ""
```

If `RevisionRequest` is already imported or defined in a route file, do not add it again.
You will need to add `from pydantic import BaseModel` if it is not already imported.

---

### 2A. Add to `backend/app/api/e2_routes.py`

Add these at the bottom of the file:

```python
from pydantic import BaseModel


class E2RevisionRequest(BaseModel):
    engineer_notes: str = ""


def _get_e2_revision_count(pipeline: PipelineState) -> int:
    counts = (pipeline.step_outputs or {}).get("revision_counts", {})
    return counts.get("e2", 0)


def _increment_e2_revision_count(pipeline: PipelineState) -> int:
    outputs = dict(pipeline.step_outputs or {})
    counts = dict(outputs.get("revision_counts", {}))
    counts["e2"] = counts.get("e2", 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = outputs
    return counts["e2"]


@router.post("/{opportunity_id}/checkpoint/revise")
def revise_e2_checkpoint(
    opportunity_id: str,
    body: E2RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an E2 revision request. Max 3 revisions.
    Does not re-run the engine — engineer must re-submit via the BoM Builder.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 21:
        raise HTTPException(
            status_code=409,
            detail="E2 not yet complete. Run E2 analysis first.",
        )
    if opportunity.status == "e2_approved":
        raise HTTPException(
            status_code=409,
            detail="E2 checkpoint already approved. Revisions are no longer possible.",
        )

    current_count = _get_e2_revision_count(pipeline)
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for E2. "
                   "Edit output files manually before approving.",
        )

    new_count = _increment_e2_revision_count(pipeline)

    # Store engineer notes for audit trail
    outputs = dict(pipeline.step_outputs)
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"e2_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes
    pipeline.step_outputs = outputs

    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "message": "Revision recorded. Re-run E2 via the BoM Builder to apply changes.",
        "rerun_url": f"/e2?session_id={opportunity_id}",
    }
```

---

### 2B. Add to `backend/app/api/e3_routes.py`

```python
from pydantic import BaseModel


class E3RevisionRequest(BaseModel):
    engineer_notes: str = ""


def _get_e3_revision_count(pipeline: PipelineState) -> int:
    counts = (pipeline.step_outputs or {}).get("revision_counts", {})
    return counts.get("e3", 0)


def _increment_e3_revision_count(pipeline: PipelineState) -> int:
    outputs = dict(pipeline.step_outputs or {})
    counts = dict(outputs.get("revision_counts", {}))
    counts["e3"] = counts.get("e3", 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = outputs
    return counts["e3"]


@router.post("/{opportunity_id}/checkpoint/revise")
def revise_e3_checkpoint(
    opportunity_id: str,
    body: E3RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an E3 revision request. Max 3 revisions.
    Engineer must re-submit via the Proposal Generator to apply changes.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 23:
        raise HTTPException(
            status_code=409,
            detail="E3 not yet complete. Generate the proposal first.",
        )
    if opportunity.status == "complete":
        raise HTTPException(
            status_code=409,
            detail="E3 checkpoint already approved. Revisions are no longer possible.",
        )

    current_count = _get_e3_revision_count(pipeline)
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for E3. "
                   "Edit output files manually before approving.",
        )

    new_count = _increment_e3_revision_count(pipeline)

    outputs = dict(pipeline.step_outputs)
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"e3_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes
    pipeline.step_outputs = outputs

    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "message": "Revision recorded. Re-run E3 via the Proposal Generator to apply changes.",
        "rerun_url": f"/e3?session_id={opportunity_id}",
    }
```

---

### 2C. Add to `backend/app/api/e4_routes.py`

```python
from pydantic import BaseModel


class E4RevisionRequest(BaseModel):
    engineer_notes: str = ""


def _get_e4_revision_count(pipeline: PipelineState) -> int:
    counts = (pipeline.step_outputs or {}).get("revision_counts", {})
    return counts.get("e4", 0)


def _increment_e4_revision_count(pipeline: PipelineState) -> int:
    outputs = dict(pipeline.step_outputs or {})
    counts = dict(outputs.get("revision_counts", {}))
    counts["e4"] = counts.get("e4", 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = outputs
    return counts["e4"]


@router.post("/{opportunity_id}/checkpoint/revise")
def revise_e4_checkpoint(
    opportunity_id: str,
    body: E4RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an E4 revision request. Max 3 revisions.
    Engineer must re-submit via the RFI Generator to apply changes.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=409,
            detail="E4 not yet complete. Generate the RFI questionnaire first.",
        )
    if opportunity.status == "e4_approved":
        raise HTTPException(
            status_code=409,
            detail="E4 checkpoint already approved. Revisions are no longer possible.",
        )

    current_count = _get_e4_revision_count(pipeline)
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for E4. "
                   "Edit output files manually before approving.",
        )

    new_count = _increment_e4_revision_count(pipeline)

    outputs = dict(pipeline.step_outputs)
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"e4_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes
    pipeline.step_outputs = outputs

    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "message": "Revision recorded. Re-run E4 via the RFI Generator to apply changes.",
        "rerun_url": f"/e4?session_id={opportunity_id}",
    }
```

---

### 2D. Add to `backend/app/api/e5_routes.py`

```python
from pydantic import BaseModel


class E5RevisionRequest(BaseModel):
    engineer_notes: str = ""


def _get_e5_revision_count(pipeline: PipelineState) -> int:
    counts = (pipeline.step_outputs or {}).get("revision_counts", {})
    return counts.get("e5", 0)


def _increment_e5_revision_count(pipeline: PipelineState) -> int:
    outputs = dict(pipeline.step_outputs or {})
    counts = dict(outputs.get("revision_counts", {}))
    counts["e5"] = counts.get("e5", 0) + 1
    outputs["revision_counts"] = counts
    pipeline.step_outputs = outputs
    return counts["e5"]


@router.post("/{opportunity_id}/checkpoint/revise")
def revise_e5_checkpoint(
    opportunity_id: str,
    body: E5RevisionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an E5 revision request. Max 3 revisions.
    Engineer must re-submit via the Design Generator to apply changes.
    """
    MAX_REVISIONS = 3

    opportunity, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 21:
        raise HTTPException(
            status_code=409,
            detail="E5 not yet complete. Generate the design document first.",
        )
    if opportunity.status == "e5_approved":
        raise HTTPException(
            status_code=409,
            detail="E5 checkpoint already approved. Revisions are no longer possible.",
        )

    current_count = _get_e5_revision_count(pipeline)
    if current_count >= MAX_REVISIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum revisions ({MAX_REVISIONS}) reached for E5. "
                   "Edit output files manually before approving.",
        )

    new_count = _increment_e5_revision_count(pipeline)

    outputs = dict(pipeline.step_outputs)
    revision_notes = dict(outputs.get("revision_notes", {}))
    revision_notes[f"e5_revision_{new_count}"] = body.engineer_notes
    outputs["revision_notes"] = revision_notes
    pipeline.step_outputs = outputs

    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "revision_number": new_count,
        "revisions_remaining": MAX_REVISIONS - new_count,
        "message": "Revision recorded. Re-run E5 via the Design Generator to apply changes.",
        "rerun_url": f"/e5?session_id={opportunity_id}",
    }
```

**Note on imports:** Each route file already imports `PipelineState`, `HTTPException`,
`Depends`, `Session`, `get_db`, and `flag_modified`. Only add `from pydantic import
BaseModel` if it is not already imported in that file. Check before adding.

---

## Step 3 — Frontend: shared RevisionModal component

Create `frontend/app/components/RevisionModal.tsx`:

```tsx
"use client";

import { useState } from "react";

type RevisionModalProps = {
  engineLabel: string;       // e.g. "E2", "E3"
  onClose: () => void;
  onSubmit: (notes: string) => void;
  submitting: boolean;
};

export default function RevisionModal({ engineLabel, onClose, onSubmit, submitting }: RevisionModalProps) {
  const [notes, setNotes] = useState("");

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
        <h3 className="mb-1 text-base font-semibold text-gray-800">Request {engineLabel} Revision</h3>
        <p className="mb-4 text-sm text-gray-500">
          Describe what needs to be corrected. After submitting, re-run the engine with updated inputs.
        </p>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={5}
          placeholder="e.g. The BoQ template used was incorrect — re-upload with the updated version."
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

---

## Step 4 — Frontend: add revision UI to each checkpoint page

For each page below, make targeted changes only. Do not rewrite the file.

The revision UI pattern for each page:
1. Import `RevisionModal`
2. Add state: `revisionCount`, `showRevisionModal`, `revisionSubmitting`, `MAX_REVISIONS = 3`
3. Read `revision_counts.{engine}` from the state fetch
4. Add `handleRevisionSubmit` function
5. Add revision counter badge + "Request Revision" button beside the approve button
6. Add `<RevisionModal>` at the bottom of the JSX

---

### 4A. Update `frontend/app/e2/[id]/page.tsx`

**Imports to add:**
```tsx
import RevisionModal from "@/app/components/RevisionModal";
```

**State to add** after existing state declarations:
```tsx
  const [revisionCount, setRevisionCount] = useState(0);
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [revisionSubmitting, setRevisionSubmitting] = useState(false);
  const MAX_REVISIONS = 3;
```

**Read revision count** in the existing `useEffect` that fetches state.
Find the `.then(data => {` block inside the useEffect and add after `setState(data)`:
```tsx
        const counts = data?.e2?.revision_counts ?? {};
        // revision_counts is stored at step_outputs level, not e2 level
        // fetch full state to get revision_counts
```

Actually, the revision_counts are in `step_outputs["revision_counts"]["e2"]`, not inside
`step_outputs["e2"]`. The `GET /api/e2/{id}/state` endpoint returns `step_outputs["e2"]`
only. Add a second fetch for the pipeline state to read revision_counts.

Add a second `useEffect` after the existing one:
```tsx
  useEffect(() => {
    fetch(`/api/e1/${encodeURIComponent(id)}/state`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.step_outputs?.revision_counts?.e2 != null) {
          setRevisionCount(data.step_outputs.revision_counts.e2);
        }
      })
      .catch(() => {});
  }, [id]);
```

Wait — there is no generic pipeline state endpoint for E2. Use the E1 state endpoint
which returns full `step_outputs` for the opportunity. That endpoint is
`GET /api/e1/{id}/state`.

**Add `handleRevisionSubmit`** after the existing `handleApprove` function:
```tsx
  async function handleRevisionSubmit(notes: string) {
    setRevisionSubmitting(true);
    try {
      const res = await fetch(`/api/e2/${encodeURIComponent(id)}/checkpoint/revise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engineer_notes: notes }),
      });
      if (res.status === 409) {
        const b = await res.json();
        setShowRevisionModal(false);
        setToast(b.detail ?? "Maximum revisions reached.");
        return;
      }
      if (!res.ok) {
        const b = await res.json();
        throw new Error(b.detail ?? `Error ${res.status}`);
      }
      const data = await res.json();
      setRevisionCount(data.revision_number);
      setShowRevisionModal(false);
      setToast(`Revision ${data.revision_number} of ${MAX_REVISIONS} recorded. ${data.message}`);
    } catch (err) {
      setShowRevisionModal(false);
      setToast(err instanceof Error ? err.message : "Revision failed.");
    } finally {
      setRevisionSubmitting(false);
    }
  }
```

**Add revision button beside approve button** in the sticky bottom bar.
Find the approve button and wrap it with a revision counter + button:
```tsx
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-end gap-1">
              {revisionCount > 0 && (
                <span className="text-xs text-gray-400">
                  Revision {revisionCount} of {MAX_REVISIONS} used
                </span>
              )}
              <button
                onClick={() => setShowRevisionModal(true)}
                disabled={approved || revisionCount >= MAX_REVISIONS}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {revisionCount >= MAX_REVISIONS ? "Max Revisions Reached" : "Request Revision"}
              </button>
            </div>
            {/* existing approve button here — unchanged */}
          </div>
```

**Add modal** at the bottom of the JSX, before the closing `</main>`:
```tsx
      {showRevisionModal && (
        <RevisionModal
          engineLabel="E2"
          onClose={() => setShowRevisionModal(false)}
          onSubmit={handleRevisionSubmit}
          submitting={revisionSubmitting}
        />
      )}
```

---

### 4B. Update `frontend/app/e3/[id]/review/page.tsx`

Same pattern. Use `GET /api/e1/{id}/state` to read `step_outputs.revision_counts.e3`.
The revise endpoint is `POST /api/e3/{id}/checkpoint/revise`.
Engine label: `"E3"`.

Add revision state, a second useEffect reading revision_counts, handleRevisionSubmit,
revision counter + button beside the approve button in the proposal summary card,
and RevisionModal at the bottom of the JSX.

The approve button in the proposal summary card currently renders inline. Add the
revision button beside it in a flex container:
```tsx
              <div className="flex items-center gap-3">
                <div className="flex flex-col items-end gap-1">
                  {revisionCount > 0 && (
                    <span className="text-xs text-gray-400">
                      Revision {revisionCount} of {MAX_REVISIONS} used
                    </span>
                  )}
                  <button
                    onClick={() => setShowRevisionModal(true)}
                    disabled={approved || revisionCount >= MAX_REVISIONS}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {revisionCount >= MAX_REVISIONS ? "Max Revisions Reached" : "Request Revision"}
                  </button>
                </div>
                {/* existing approve button — unchanged */}
              </div>
```

---

### 4C. Update `frontend/app/e4/[id]/page.tsx`

Same pattern. Use `GET /api/e1/{id}/state` to read `step_outputs.revision_counts.e4`.
Revise endpoint: `POST /api/e4/{id}/checkpoint/revise`.
Engine label: `"E4"`.

Add revision state + second useEffect + handleRevisionSubmit.
Add revision counter + button beside the approve button in the sticky bottom bar.
Add RevisionModal.

---

### 4D. Update `frontend/app/e5/[id]/page.tsx`

Same pattern. Use `GET /api/e1/{id}/state` to read `step_outputs.revision_counts.e5`.
Revise endpoint: `POST /api/e5/{id}/checkpoint/revise`.
Engine label: `"E5"`.

Add revision state + second useEffect + handleRevisionSubmit.
Add revision counter + button beside the approve button in the design summary card.
Add RevisionModal.

---

## Step 5 — Validation steps

### 5A. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e2_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e3_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e4_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e5_routes.py
```
Expected: no output.

### 5B. Import check
```
backend\.venv\Scripts\python.exe -c "
from app.api.e2_routes import revise_e2_checkpoint
from app.api.e3_routes import revise_e3_checkpoint
from app.api.e4_routes import revise_e4_checkpoint
from app.api.e5_routes import revise_e5_checkpoint
print('all revision imports OK')
"
```
Expected: `all revision imports OK`

### 5C. Route smoke test
```
backend\.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, 'backend')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
headers = {'X-API-Key': 'bomatic-dev-key'}

for engine in ['e2', 'e3', 'e4', 'e5']:
    r = client.post(
        f'/api/{engine}/NONEXISTENT/checkpoint/revise',
        json={'engineer_notes': 'test'},
        headers=headers,
    )
    assert r.status_code == 404, f'{engine} revise: expected 404 got {r.status_code}: {r.text}'
    print(f'{engine} revise 404: PASS')

print('All route checks passed.')
"
```
Expected: 4 PASS lines then `All route checks passed.`

### 5D. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 5E. Frontend build
```
cd frontend && npm run build
```
Expected: zero errors. `RevisionModal` appears in build output.

### 5F. Max revision enforcement test
Using FastAPI TestClient, create an opportunity with E2 complete, call revise 3 times,
assert 4th call returns 409:

```
backend\.venv\Scripts\python.exe -c "
import sys, uuid
sys.path.insert(0, 'backend')
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState

client = TestClient(app)
headers = {'X-API-Key': 'bomatic-dev-key'}
opp_id = f'REV-{uuid.uuid4().hex[:6].upper()}'

# Create opportunity + pipeline with e2 complete state
db = SessionLocal()
try:
    opp = Opportunity(opportunity_id=opp_id, project_name='Revision Test',
                      status='e2_complete', mode='rfp')
    db.add(opp)
    db.flush()
    ps = PipelineState(opportunity_id=opp.id, current_step=21,
                       step_outputs={'e2': {'matched_count': 5, 'total': 1000}})
    db.add(ps)
    db.commit()
finally:
    db.close()

# 3 revisions should succeed
for i in range(1, 4):
    r = client.post(f'/api/e2/{opp_id}/checkpoint/revise',
                    json={'engineer_notes': f'Revision {i}'},
                    headers=headers)
    assert r.status_code == 200, f'Revision {i} failed: {r.text}'
    assert r.json()['revision_number'] == i
    print(f'Revision {i}: PASS')

# 4th should return 409
r = client.post(f'/api/e2/{opp_id}/checkpoint/revise',
                json={'engineer_notes': 'too many'},
                headers=headers)
assert r.status_code == 409, f'Expected 409 got {r.status_code}'
print('4th revision 409: PASS')

print('Max revision enforcement: PASS')
"
```
Expected: 3 revision PASS lines + `4th revision 409: PASS` + final PASS.

---

## Step 6 — Summary of files changed

| Action   | File path                                        |
|----------|--------------------------------------------------|
| Modified | `backend/app/api/e2_routes.py`                   |
| Modified | `backend/app/api/e3_routes.py`                   |
| Modified | `backend/app/api/e4_routes.py`                   |
| Modified | `backend/app/api/e5_routes.py`                   |
| Created  | `frontend/app/components/RevisionModal.tsx`      |
| Modified | `frontend/app/e2/[id]/page.tsx`                  |
| Modified | `frontend/app/e3/[id]/review/page.tsx`           |
| Modified | `frontend/app/e4/[id]/page.tsx`                  |
| Modified | `frontend/app/e5/[id]/page.tsx`                  |

No DB migration. No new dependencies.

---

## Step 7 — Git commit message

```
feat: add F5 revision loops for E2, E3, E4, E5 checkpoints

Backend:
- e2/e3/e4/e5_routes.py: POST /{id}/checkpoint/revise endpoint
  Records engineer notes, increments revision_counts["{engine}"] in
  step_outputs, enforces max 3 revisions (409 on 4th attempt), returns
  revision_number + revisions_remaining + rerun_url
  Returns 409 if engine not yet complete or already approved

Frontend:
- RevisionModal.tsx: shared modal component with engine label, notes
  textarea, cancel + submit buttons
- e2/e3/e4/e5 checkpoint pages: import RevisionModal; add revisionCount
  state read from step_outputs.revision_counts via e1 state endpoint;
  handleRevisionSubmit calling the revise endpoint; revision counter badge
  and button beside approve button; modal rendered at bottom of JSX
```
