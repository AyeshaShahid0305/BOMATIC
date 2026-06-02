# Codex Task: Checkpoint UIs for E2, E3, E4, E5

## Context

BOMATIC is a FastAPI + Next.js + PostgreSQL pre-sales platform. E1 has full
checkpoint UIs (checkpoint1 + checkpoint2 pages with data display, approve buttons,
and revision loops). E2/E3/E4/E5 have only thin pages showing "complete" status
and download buttons — no output data is displayed and there is no approve button.

This task adds:
1. **State endpoints** (`GET /api/e{n}/{id}/state`) for E2/E3/E4/E5 — read
   step_outputs for the engine.
2. **Approve endpoints** (`POST /api/e{n}/{id}/checkpoint/approve`) — advance
   pipeline and return a navigation hint.
3. **Fixed E2 storage** — e2_routes currently stores `total_price` (always 0) and
   `matched_items` (always []) because it reads wrong keys from the pipeline result.
   Fix this at the same time.
4. **Enhanced frontend pages** — show actual output data + approve button.
   - `frontend/app/e2/[id]/page.tsx` — add stats cards + approve
   - `frontend/app/e3/[id]/review/page.tsx` — add section summary + approve
   - Create `frontend/app/e4/[id]/page.tsx` — new page (does not exist)
   - `frontend/app/e5/[id]/page.tsx` — add stats + approve

Approval is purely an acknowledgment — no additional computation. It sets
`opportunity.status` and increments `current_step` by 1, then returns a
`next_url` for the engineer to follow.

---

## Step 1 — Read these files first (in this order)

1. `backend/app/api/e2_routes.py`
2. `backend/app/api/e3_routes.py`
3. `backend/app/api/e4_routes.py`
4. `backend/app/api/e5_routes.py`
5. `backend/app/engines/e2/pipeline.py`
6. `backend/app/models/opportunity.py`
7. `backend/app/models/pipeline_state.py`
8. `frontend/app/e2/[id]/page.tsx`
9. `frontend/app/e3/[id]/review/page.tsx`
10. `frontend/app/e5/[id]/page.tsx`
11. `frontend/app/e1/[id]/checkpoint1/page.jsx` — reference for UI pattern

---

## Step 2 — Backend: Fix E2 storage + add state and approve endpoints

### 2A. Fix `backend/app/api/e2_routes.py`

**Fix 1 — Correct the step_outputs["e2"] keys.**

The pipeline returns `matched_count`, `unmatched_count`, `total`, `currency`, and
`discount_amount` — but the route stores `matched_items` (always []) and
`total_price` (always 0). Fix by replacing the storage block:

Find:
```python
            outputs['e2'] = {
                'matched_items': result.get('matched_items', []),
                'subtotal': result.get('subtotal', 0),
                'total_price': result.get('total_price', 0),
                'vendor_list': result.get('vendor_list', []),
                'requirements_baseline_count': result.get('requirements_baseline_count', 0),
                'output_file': Path(result['output_file']).name,
                'distributor_file': result.get('distributor_file') or '',
            }
```

Replace with:
```python
            outputs['e2'] = {
                'matched_count': result.get('matched_count', 0),
                'unmatched_count': result.get('unmatched_count', 0),
                'low_confidence_count': result.get('low_confidence_count', 0),
                'subtotal': result.get('subtotal', 0),
                'discount_amount': result.get('discount_amount', 0),
                'total': result.get('total', 0),
                'currency': result.get('currency', 'USD'),
                'vendor_list': result.get('vendor_list', []),
                'requirements_baseline_count': result.get('requirements_baseline_count', 0),
                'output_file': Path(result['output_file']).name,
                'distributor_file': result.get('distributor_file') or '',
            }
```

**Fix 2 — Add state and approve endpoints.**

Add these two functions at the bottom of `e2_routes.py`:

```python
def _get_e2_opportunity_and_pipeline(opportunity_id: str, db: Session):
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == opportunity_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' not found.")
    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline state not found.")
    return opportunity, pipeline


@router.get("/{opportunity_id}/state")
def get_e2_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return E2 step outputs and opportunity info."""
    opportunity, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)
    e2_data = (pipeline.step_outputs or {}).get("e2")
    if not e2_data:
        raise HTTPException(status_code=404, detail="E2 has not been run for this opportunity.")
    return {
        "opportunity_id": opportunity_id,
        "project_name": opportunity.project_name,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "e2": e2_data,
    }


@router.post("/{opportunity_id}/checkpoint/approve")
def approve_e2_checkpoint(opportunity_id: str, db: Session = Depends(get_db)):
    """Approve the E2 checkpoint. Advances pipeline and returns next URL."""
    opportunity, pipeline = _get_e2_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 21:
        raise HTTPException(
            status_code=409,
            detail="E2 not yet complete. Run E2 analysis first.",
        )
    if opportunity.status == "e2_approved":
        raise HTTPException(status_code=409, detail="E2 checkpoint already approved.")

    opportunity.status = "e2_approved"
    pipeline.current_step = max(pipeline.current_step, 22)
    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "status": "e2_approved",
        "next_url": f"/e3?session_id={opportunity_id}",
        "message": "E2 approved. Proceed to E3 proposal generation.",
    }
```

---

### 2B. Add state and approve endpoints to `backend/app/api/e3_routes.py`

Add these at the bottom of the file. The same helper pattern — check if `e3` key
exists in step_outputs, return 404 if not.

```python
def _get_e3_opportunity_and_pipeline(opportunity_id: str, db: Session):
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == opportunity_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' not found.")
    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline state not found.")
    return opportunity, pipeline


@router.get("/{opportunity_id}/state")
def get_e3_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return E3 step outputs and opportunity info."""
    opportunity, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)
    e3_data = (pipeline.step_outputs or {}).get("e3")
    if not e3_data:
        raise HTTPException(status_code=404, detail="E3 has not been run for this opportunity.")
    return {
        "opportunity_id": opportunity_id,
        "project_name": opportunity.project_name,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "e3": e3_data,
    }


@router.post("/{opportunity_id}/checkpoint/approve")
def approve_e3_checkpoint(opportunity_id: str, db: Session = Depends(get_db)):
    """Approve the E3 checkpoint. Marks the pipeline complete."""
    opportunity, pipeline = _get_e3_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 23:
        raise HTTPException(
            status_code=409,
            detail="E3 not yet complete. Generate the proposal first.",
        )
    if opportunity.status == "complete":
        raise HTTPException(status_code=409, detail="E3 checkpoint already approved.")

    opportunity.status = "complete"
    pipeline.current_step = max(pipeline.current_step, 24)
    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "status": "complete",
        "next_url": f"/opportunities",
        "message": "Proposal approved. Opportunity is complete.",
    }
```

Also add the missing `flag_modified` import at the top of `e3_routes.py` if it is
not already there:
```python
from sqlalchemy.orm.attributes import flag_modified
```

---

### 2C. Add state and approve endpoints to `backend/app/api/e4_routes.py`

Same pattern. Add at the bottom:

```python
def _get_e4_opportunity_and_pipeline(opportunity_id: str, db: Session):
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == opportunity_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' not found.")
    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline state not found.")
    return opportunity, pipeline


@router.get("/{opportunity_id}/state")
def get_e4_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return E4 step outputs and opportunity info."""
    opportunity, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)
    e4_data = (pipeline.step_outputs or {}).get("e4")
    if not e4_data:
        raise HTTPException(status_code=404, detail="E4 has not been run for this opportunity.")
    return {
        "opportunity_id": opportunity_id,
        "project_name": opportunity.project_name,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "e4": e4_data,
    }


@router.post("/{opportunity_id}/checkpoint/approve")
def approve_e4_checkpoint(opportunity_id: str, db: Session = Depends(get_db)):
    """Approve the E4 checkpoint. Returns next URL (E5 design)."""
    opportunity, pipeline = _get_e4_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 11:
        raise HTTPException(
            status_code=409,
            detail="E4 not yet complete. Generate the RFI questionnaire first.",
        )
    if opportunity.status == "e4_approved":
        raise HTTPException(status_code=409, detail="E4 checkpoint already approved.")

    opportunity.status = "e4_approved"
    pipeline.current_step = max(pipeline.current_step, 12)
    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "status": "e4_approved",
        "next_url": f"/e5?session_id={opportunity_id}",
        "message": "E4 approved. Proceed to E5 design generation.",
    }
```

Also add the missing `flag_modified` import if not already present:
```python
from sqlalchemy.orm.attributes import flag_modified
```

---

### 2D. Add state and approve endpoints to `backend/app/api/e5_routes.py`

Same pattern:

```python
def _get_e5_opportunity_and_pipeline(opportunity_id: str, db: Session):
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.opportunity_id == opportunity_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' not found.")
    pipeline = (
        db.query(PipelineState)
        .filter(PipelineState.opportunity_id == opportunity.id)
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline state not found.")
    return opportunity, pipeline


@router.get("/{opportunity_id}/state")
def get_e5_state(opportunity_id: str, db: Session = Depends(get_db)):
    """Return E5 step outputs and opportunity info."""
    opportunity, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)
    e5_data = (pipeline.step_outputs or {}).get("e5")
    if not e5_data:
        raise HTTPException(status_code=404, detail="E5 has not been run for this opportunity.")
    return {
        "opportunity_id": opportunity_id,
        "project_name": opportunity.project_name,
        "status": opportunity.status,
        "current_step": pipeline.current_step,
        "e5": e5_data,
    }


@router.post("/{opportunity_id}/checkpoint/approve")
def approve_e5_checkpoint(opportunity_id: str, db: Session = Depends(get_db)):
    """Approve the E5 checkpoint. Returns next URL (E2 BoM for RFI mode)."""
    opportunity, pipeline = _get_e5_opportunity_and_pipeline(opportunity_id, db)

    if pipeline.current_step < 21:
        raise HTTPException(
            status_code=409,
            detail="E5 not yet complete. Generate the design document first.",
        )
    if opportunity.status == "e5_approved":
        raise HTTPException(status_code=409, detail="E5 checkpoint already approved.")

    opportunity.status = "e5_approved"
    pipeline.current_step = max(pipeline.current_step, 22)
    flag_modified(pipeline, "step_outputs")
    db.commit()

    return {
        "opportunity_id": opportunity_id,
        "status": "e5_approved",
        "next_url": f"/e2?session_id={opportunity_id}",
        "message": "E5 approved. Proceed to E2 BoM generation.",
    }
```

---

## Step 3 — Frontend: Update `frontend/app/e2/[id]/page.tsx`

Replace the entire file with this content:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import DownloadButton from "@/app/components/DownloadButton";

type E2Data = {
  matched_count: number;
  unmatched_count: number;
  low_confidence_count: number;
  subtotal: number;
  discount_amount: number;
  total: number;
  currency: string;
  vendor_list: string[];
  requirements_baseline_count: number;
};

type E2State = {
  opportunity_id: string;
  project_name: string | null;
  status: string;
  current_step: number;
  e2: E2Data;
};

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

function Spinner() {
  return (
    <svg className="h-5 w-5 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

function fmt(n: number, currency: string) {
  return `${currency} ${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function E2CheckpointPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<E2State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/e2/${encodeURIComponent(id)}/state`)
      .then(async r => {
        if (!r.ok) {
          const b = await r.json().catch(() => null);
          throw new Error(b?.detail ?? `Error ${r.status}`);
        }
        return r.json();
      })
      .then(data => {
        setState(data);
        if (data.status === "e2_approved") setApproved(true);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleApprove() {
    setApproving(true);
    try {
      const res = await fetch(`/api/e2/${encodeURIComponent(id)}/checkpoint/approve`, { method: "POST" });
      if (!res.ok) {
        const b = await res.json();
        throw new Error(b.detail ?? `Error ${res.status}`);
      }
      const data = await res.json();
      setApproved(true);
      setToast(data.message);
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Approval failed.");
    } finally {
      setApproving(false);
    }
  }

  const e2 = state?.e2;
  const currency = e2?.currency ?? "USD";

  return (
    <main className="min-h-screen bg-gray-50 pb-28 px-6 py-10">
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Breadcrumb + title */}
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/" className="hover:text-gray-800">BOMATIC</a>
            <span>/</span>
            <a href="/opportunities" className="hover:text-gray-800">Opportunities</a>
            <span>/</span>
            <span className="font-medium text-gray-800">E2 Checkpoint</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">E2 — Bill of Materials Review</h1>
          <p className="mt-1 text-sm text-gray-500">Opportunity {id}</p>
        </div>

        {loading && <p className="text-sm text-gray-400">Loading…</p>}
        {error && <p className="text-sm text-red-700">{error}</p>}

        {!loading && !error && state && e2 && (
          <>
            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard label="Matched" value={String(e2.matched_count)} sub="items catalogued" />
              <StatCard label="Unmatched" value={String(e2.unmatched_count)} sub="need manual review" />
              <StatCard label="Subtotal" value={fmt(e2.subtotal, currency)} />
              <StatCard label="Total" value={fmt(e2.total, currency)} sub={`after ${fmt(e2.discount_amount, currency)} discount`} />
            </div>

            {/* Vendors */}
            {e2.vendor_list.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Vendors Identified</p>
                <div className="flex flex-wrap gap-2">
                  {e2.vendor_list.map(v => (
                    <span key={v} className="rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">{v}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Unmatched warning */}
            {e2.unmatched_count > 0 && (
              <div className="rounded-xl border border-orange-200 bg-orange-50 px-5 py-4 text-sm text-orange-800">
                <span className="font-semibold">{e2.unmatched_count} item(s)</span> could not be matched to the catalog.
                Download the BoM workbook and fill in the highlighted <span className="font-mono">NEEDS REVIEW</span> rows before approving.
              </div>
            )}

            {/* Downloads */}
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Downloads</p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <DownloadButton opportunityId={id} filename="bom_workbook.xlsx" label="Download BoM Workbook" />
                <DownloadButton opportunityId={id} filename="distributor_export.xlsx" label="Download Distributor Export" />
              </div>
            </div>

            {/* Approved banner */}
            {approved && (
              <div className="rounded-xl border border-green-200 bg-green-50 px-5 py-4 text-sm font-medium text-green-800">
                ✓ E2 approved. <a href={`/e3?session_id=${encodeURIComponent(id)}`} className="underline font-semibold">Generate the Technical Proposal →</a>
              </div>
            )}
          </>
        )}

        {toast && (
          <div className="rounded-xl border border-blue-200 bg-blue-50 px-5 py-3 text-sm text-blue-800">{toast}</div>
        )}
      </div>

      {/* Sticky bottom bar */}
      {!loading && !error && state && (
        <div className="fixed bottom-0 left-0 right-0 border-t border-gray-200 bg-white px-6 py-4 shadow-lg">
          <div className="mx-auto flex max-w-4xl items-center justify-between">
            <a href="/opportunities" className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              ← Opportunities
            </a>
            <button
              onClick={handleApprove}
              disabled={approving || approved}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {approving && <Spinner />}
              {approved ? "Approved" : approving ? "Approving…" : "Approve & Continue to E3"}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
```

---

## Step 4 — Frontend: Update `frontend/app/e3/[id]/review/page.tsx`

Make two targeted changes only. Do not rewrite the file.

**Change 1 — Add E3 state fetch alongside the existing packages fetch.**

Find the `useEffect` that fetches package state:
```tsx
  useEffect(() => {
    fetch(`/api/v1/rfp/packages/${encodeURIComponent(id)}`)
```

Add a second state variable and second fetch for E3 data. Add after the existing
`const [state, setState]` line:
```tsx
  const [e3Data, setE3Data] = useState<{section_count: number; ai_generated_count?: number; gbb_tier?: string; total_price?: number} | null>(null);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);
```

After the existing `useEffect`, add a second `useEffect` for E3 state:
```tsx
  useEffect(() => {
    fetch(`/api/e3/${encodeURIComponent(id)}/state`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.e3) setE3Data(data.e3);
        if (data?.status === "complete") setApproved(true);
      })
      .catch(() => {});
  }, [id]);
```

**Change 2 — Add approve button and E3 summary to the existing card.**

Find the closing `</div>` of the downloads section card:
```tsx
        {e3Complete && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Downloads
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <DownloadButton ... />
              <DownloadButton ... />
            </div>
          </div>
        )}
```

Add after it:
```tsx
        {e3Complete && e3Data && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Proposal Summary</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs text-gray-400">Sections</p>
                <p className="text-xl font-bold text-gray-900">{e3Data.section_count}</p>
              </div>
              {e3Data.gbb_tier && (
                <div>
                  <p className="text-xs text-gray-400">GBB Tier</p>
                  <p className="text-xl font-bold text-gray-900 capitalize">{e3Data.gbb_tier}</p>
                </div>
              )}
              {e3Data.total_price != null && (
                <div>
                  <p className="text-xs text-gray-400">Total Price</p>
                  <p className="text-xl font-bold text-gray-900">
                    {e3Data.total_price.toLocaleString("en-US", { style: "currency", currency: "USD" })}
                  </p>
                </div>
              )}
            </div>
            <div className="mt-5 flex items-center justify-between">
              {approved ? (
                <span className="rounded-full bg-green-100 px-4 py-1.5 text-sm font-semibold text-green-700">✓ Approved — Complete</span>
              ) : (
                <button
                  onClick={async () => {
                    setApproving(true);
                    try {
                      const res = await fetch(`/api/e3/${encodeURIComponent(id)}/checkpoint/approve`, { method: "POST" });
                      if (res.ok) setApproved(true);
                    } finally { setApproving(false); }
                  }}
                  disabled={approving}
                  className="rounded-lg bg-green-600 px-5 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                >
                  {approving ? "Approving…" : "Approve & Mark Complete"}
                </button>
              )}
            </div>
          </div>
        )}
```

---

## Step 5 — Frontend: Create `frontend/app/e4/[id]/page.tsx`

Create this new file:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import DownloadButton from "@/app/components/DownloadButton";

type E4Data = {
  project_name: string;
  total_questions: number;
  categories: string[];
  must_have_count: number;
  nice_to_have_count: number;
  output_file: string;
};

type E4State = {
  opportunity_id: string;
  project_name: string | null;
  status: string;
  current_step: number;
  e4: E4Data;
};

function Spinner() {
  return (
    <svg className="h-5 w-5 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

export default function E4CheckpointPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<E4State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);

  useEffect(() => {
    fetch(`/api/e4/${encodeURIComponent(id)}/state`)
      .then(async r => {
        if (!r.ok) {
          const b = await r.json().catch(() => null);
          throw new Error(b?.detail ?? `Error ${r.status}`);
        }
        return r.json();
      })
      .then(data => {
        setState(data);
        if (data.status === "e4_approved") setApproved(true);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleApprove() {
    setApproving(true);
    try {
      const res = await fetch(`/api/e4/${encodeURIComponent(id)}/checkpoint/approve`, { method: "POST" });
      if (!res.ok) {
        const b = await res.json();
        throw new Error(b.detail ?? `Error ${res.status}`);
      }
      setApproved(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Approval failed.");
    } finally {
      setApproving(false);
    }
  }

  const e4 = state?.e4;

  return (
    <main className="min-h-screen bg-gray-50 pb-28 px-6 py-10">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/" className="hover:text-gray-800">BOMATIC</a>
            <span>/</span>
            <a href="/opportunities" className="hover:text-gray-800">Opportunities</a>
            <span>/</span>
            <span className="font-medium text-gray-800">E4 Checkpoint</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">E4 — RFI Questionnaire Review</h1>
          <p className="mt-1 text-sm text-gray-500">Opportunity {id}</p>
        </div>

        {loading && <p className="text-sm text-gray-400">Loading…</p>}
        {error && <p className="text-sm text-red-700">{error}</p>}

        {!loading && !error && e4 && (
          <>
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Total Questions</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{e4.total_questions}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Must-Have</p>
                <p className="mt-1 text-2xl font-bold text-blue-700">{e4.must_have_count}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Nice-to-Have</p>
                <p className="mt-1 text-2xl font-bold text-gray-600">{e4.nice_to_have_count}</p>
              </div>
            </div>

            {e4.categories.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Categories</p>
                <div className="flex flex-wrap gap-2">
                  {e4.categories.map((c: string) => (
                    <span key={c} className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700">{c}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Downloads</p>
              <DownloadButton opportunityId={id} filename="rfi_questionnaire.xlsx" label="Download RFI Questionnaire" />
            </div>

            {approved && (
              <div className="rounded-xl border border-green-200 bg-green-50 px-5 py-4 text-sm font-medium text-green-800">
                ✓ E4 approved. <a href={`/e5?session_id=${encodeURIComponent(id)}`} className="underline font-semibold">Generate the HLD/LLD Design →</a>
              </div>
            )}
          </>
        )}
      </div>

      {!loading && !error && e4 && (
        <div className="fixed bottom-0 left-0 right-0 border-t border-gray-200 bg-white px-6 py-4 shadow-lg">
          <div className="mx-auto flex max-w-3xl items-center justify-between">
            <a href="/opportunities" className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              ← Opportunities
            </a>
            <button
              onClick={handleApprove}
              disabled={approving || approved}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {approving && <Spinner />}
              {approved ? "Approved" : approving ? "Approving…" : "Approve & Continue to E5"}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
```

---

## Step 6 — Frontend: Update `frontend/app/e5/[id]/page.tsx`

Make two targeted changes. Do not rewrite the file.

**Change 1 — Add approve state variables** after the existing state declarations:
```tsx
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);
  const [e5Data, setE5Data] = useState<{total_sections: number; project_name: string} | null>(null);
```

**Change 2 — Add a second useEffect** to fetch E5 state, after the existing useEffect:
```tsx
  useEffect(() => {
    fetch(`/api/e5/${encodeURIComponent(id)}/state`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.e5) setE5Data(data.e5);
        if (data?.status === "e5_approved") setApproved(true);
      })
      .catch(() => {});
  }, [id]);
```

**Change 3 — Add approve button and stats** after the existing download card.

Find the closing `</div>` of the downloads card and add after it:
```tsx
        {e5Complete && e5Data && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Design Summary</p>
            <p className="text-2xl font-bold text-gray-900">{e5Data.total_sections} <span className="text-base font-normal text-gray-500">sections generated</span></p>
            <div className="mt-4 flex items-center justify-between">
              {approved ? (
                <span className="rounded-full bg-green-100 px-4 py-1.5 text-sm font-semibold text-green-700">
                  ✓ Approved — proceed to E2
                </span>
              ) : (
                <button
                  onClick={async () => {
                    setApproving(true);
                    try {
                      const res = await fetch(`/api/e5/${encodeURIComponent(id)}/checkpoint/approve`, { method: "POST" });
                      if (res.ok) setApproved(true);
                    } finally { setApproving(false); }
                  }}
                  disabled={approving}
                  className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {approving ? "Approving…" : "Approve & Continue to E2 BoM"}
                </button>
              )}
            </div>
          </div>
        )}
```

---

## Step 7 — Validation steps

### 7A. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e2_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e3_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e4_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e5_routes.py
```
Expected: no output.

### 7B. Import check
```
backend\.venv\Scripts\python.exe -c "
from app.api.e2_routes import get_e2_state, approve_e2_checkpoint
from app.api.e3_routes import get_e3_state, approve_e3_checkpoint
from app.api.e4_routes import get_e4_state, approve_e4_checkpoint
from app.api.e5_routes import get_e5_state, approve_e5_checkpoint
print('all imports OK')
"
```
Expected: `all imports OK`

### 7C. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 7D. Frontend build
```
cd frontend && npm run build
```
Expected: zero errors. `e4/[id]` appears in the build output as a new page.

### 7E. FastAPI route check
```
backend\.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, 'backend')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
headers = {'X-API-Key': 'bomatic-dev-key'}

# State endpoints return 404 for non-existent opportunity (not 500)
for engine in ['e2', 'e3', 'e4', 'e5']:
    r = client.get(f'/api/{engine}/NONEXISTENT/state', headers=headers)
    assert r.status_code == 404, f'{engine} state: expected 404, got {r.status_code}'
    print(f'{engine} state 404: PASS')

# Approve endpoints return 404 for non-existent opportunity
for engine in ['e2', 'e3', 'e4', 'e5']:
    r = client.post(f'/api/{engine}/NONEXISTENT/checkpoint/approve', headers=headers)
    assert r.status_code == 404, f'{engine} approve: expected 404, got {r.status_code}'
    print(f'{engine} approve 404: PASS')

print('All route checks passed.')
"
```
Expected: 8 PASS lines then `All route checks passed.`

---

## Step 8 — Summary of files changed

| Action   | File path                                      |
|----------|------------------------------------------------|
| Modified | `backend/app/api/e2_routes.py`                 |
| Modified | `backend/app/api/e3_routes.py`                 |
| Modified | `backend/app/api/e4_routes.py`                 |
| Modified | `backend/app/api/e5_routes.py`                 |
| Modified | `frontend/app/e2/[id]/page.tsx`                |
| Modified | `frontend/app/e3/[id]/review/page.tsx`         |
| Created  | `frontend/app/e4/[id]/page.tsx`                |
| Modified | `frontend/app/e5/[id]/page.tsx`                |

No DB migration. No new dependencies.

---

## Step 9 — Git commit message

```
feat: add checkpoint UIs and approve endpoints for E2, E3, E4, E5

Backend:
- e2_routes.py: fix step_outputs["e2"] storage (matched_count, unmatched_count,
  total, currency, discount_amount replacing incorrect matched_items/total_price);
  add GET /{id}/state and POST /{id}/checkpoint/approve
- e3_routes.py: add GET /{id}/state and POST /{id}/checkpoint/approve
  (approve sets status="complete", step=24)
- e4_routes.py: add GET /{id}/state and POST /{id}/checkpoint/approve
  (approve sets status="e4_approved", step=12, next=E5)
- e5_routes.py: add GET /{id}/state and POST /{id}/checkpoint/approve
  (approve sets status="e5_approved", step=22, next=E2)

Frontend:
- e2/[id]/page.tsx: full rewrite — stats cards (matched/unmatched/subtotal/total),
  vendor badges, unmatched warning, downloads, approve button
- e3/[id]/review/page.tsx: add E3 state fetch, proposal summary card,
  approve button
- e4/[id]/page.tsx: new page — question counts, category badges,
  download, approve button
- e5/[id]/page.tsx: add E5 state fetch, section count summary, approve button
```
