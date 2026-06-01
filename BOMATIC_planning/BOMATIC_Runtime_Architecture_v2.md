# BOMATIC Runtime Architecture v2

**Status:** Reference spec for implementation  
**Scope:** Opportunities dashboard, pipeline coordinator, human checkpoints for E2–E5  
**Derived from:** Live codebase audit — `backend/app/models/`, `backend/app/api/`, `backend/app/engines/`

---

## 1. Opportunity Status Lifecycle

### All status values and what writes them

| Status | Written by | Meaning |
|---|---|---|
| `uploaded` | `POST /api/v1/rfp/packages` | Files received, `Document` and `PipelineState` records created, `current_step = 0` |
| `checkpoint_1_pending` | `POST /api/e1/{id}/run` | Steps 1–4 complete (`current_step = 4`). Awaiting engineer review before compliance mapping |
| `checkpoint_2_pending` | `POST /api/e1/{id}/checkpoint1/approve` | Steps 8–11 complete (`current_step = 11`). Compliance matrix generated; awaiting engineer validation |
| `e1_complete` | `POST /api/e1/{id}/checkpoint2/approve` | XLSX written (`current_step = 12`). E1 fully done. **Currently writes `complete` — should be changed to `e1_complete`** |
| `e2_pending` | Pipeline coordinator (to be built) | E1 approved; coordinator has triggered E2 |
| `e2_complete` | Pipeline coordinator (to be built) | E2 BoM output approved by engineer |
| `e3_pending` | Pipeline coordinator (to be built) | E2 approved; coordinator has triggered E3 |
| `e3_complete` | Pipeline coordinator (to be built) | E3 proposal approved by engineer |
| `complete` | Pipeline coordinator (to be built) | All selected engines finished and approved |

### Current issue

`checkpoint2_approve` sets `status = "complete"` after E1 alone. This conflicts with the multi-engine flow. **Fix:** change that line to `opportunity.status = "e1_complete"` and reserve `"complete"` for the full pipeline end state.

### State machine (linear path)

```
uploaded
  → [POST /e1/{id}/run]
checkpoint_1_pending
  → [POST /e1/{id}/checkpoint1/approve]
checkpoint_2_pending
  → [POST /e1/{id}/checkpoint2/approve]
e1_complete
  → [coordinator triggers E2]
e2_pending
  → [POST /e2/{id}/checkpoint/approve]
e2_complete
  → [coordinator triggers E3]
e3_pending
  → [POST /e3/{id}/checkpoint/approve]
e3_complete
  → [mark complete or run E4/E5 in parallel]
complete
```

E4 and E5 are not sequentially dependent on E2/E3. They can run in parallel after `e1_complete`. The coordinator should support a `run_engines` parameter specifying which engines to trigger (e.g., `["e2", "e3"]` or `["e1", "e2", "e3", "e4", "e5"]`).

---

## 2. `step_outputs` Structure Across E1–E5

`step_outputs` is a JSONB column on `PipelineState`. All engines read from and write to this dict. Keys must never collide across engines.

### E1 — written by `e1_router.py`

Written across three calls: `/run`, `/checkpoint1/approve`, `/checkpoint2/approve`.

```json
{
  "1": [
    {
      "filename": "Purchase_Requisition.docx",
      "type": "technical",
      "subtype": "requirements",
      "confidence": 0.95,
      "stage_used": "filename",
      "needs_human_review": false,
      "can_auto_process": true
    }
  ],
  "2": [
    {
      "referenced_doc": "SACS-002",
      "referenced_in": "Purchase_Requisition.docx",
      "page": 14,
      "line": "shall comply with SACS-002",
      "severity": "critical",
      "action": "Request from client"
    }
  ],
  "3": [
    {
      "id": "R-001",
      "text": "Vendor shall provide 24×7 support",
      "classification": "mandatory",
      "confidence": 0.95,
      "source_file": "Purchase_Requisition.docx",
      "page": 3,
      "indicators": ["shall"],
      "section": "Support Requirements",
      "related_standards": ["NCA_ECC"]
    }
  ],
  "4": [
    {
      "flag": "Bid bond of 2% required",
      "severity": "critical",
      "source": "T&C §3.2",
      "deadline": "2026-03-15",
      "days_remaining": 45
    }
  ],
  "5": {
    "criteria": [],
    "methodology": "sequential_envelope"
  },
  "8": {
    "sector": "oil_and_gas",
    "confidence": 0.95,
    "method": "client_lookup",
    "evidence": "Saudi Aramco"
  },
  "9": ["NCA_ECC", "SACS-002", "ISO_27001"],
  "10": [
    {
      "req_id": "R-001",
      "req_text": "Vendor shall provide 24×7 support",
      "classification": "mandatory",
      "framework": "NCA_ECC",
      "control_id": "2-9-1",
      "control_name": "Incident Response",
      "status": "Compliant",
      "tp_section": "§8",
      "notes": "",
      "gap_type": "none"
    }
  ],
  "gaps": {
    "coverage_gaps": ["NCA ECC 2-8 (Cryptography)"],
    "orphan_requirements": ["R-037"]
  },
  "stats": {
    "total_requirements": 42,
    "mandatory": 28,
    "optional": 10,
    "conditional": 4,
    "compliant": 25,
    "partial": 3,
    "non_compliant": 0
  },
  "xlsx_path": "/app/storage/OP-2025-001/e1_OP-2025-001_compliance_matrix_v1.xlsx"
}
```

**Note:** Keys `6` and `7` are intentionally absent (reserved for future steps per the router comment).

### E2 — written by `e2_routes.py`

Written under a single top-level key `"e2"` — does not use numbered step keys.

```json
{
  "e2": {
    "matched_items": [
      {
        "rfp_item": { "description": "Cisco Catalyst 9300", "quantity": 10, "unit": "each", "category": "switching", "raw_text": "...", "confidence": 0.9 },
        "sku": "C9300-48U-A",
        "product_name": "Cisco Catalyst 9300 48-Port",
        "vendor": "Cisco",
        "unit_price": 4200.0,
        "match_score": 0.92,
        "match_method": "fuzzy"
      }
    ],
    "subtotal": 42000.0,
    "total_price": 39900.0,
    "output_file": "boq_output_OP-2025-001.xlsx"
  }
}
```

**Current issue:** E2 does not advance `Opportunity.status`. The coordinator must do this. E2 also has no concept of a checkpoint — it runs to completion and returns immediately. The checkpoint is a new feature to build (see Section 3).

### E3 — not yet persisted to `step_outputs`

E3's `generate_proposal` route does **not** write to `step_outputs`. It reads from `step_outputs["e2"]` and `Document.text_content`, runs the pipeline, and returns a filename. The coordinator must persist E3's result.

Add key `"e3"` to `step_outputs` after a successful E3 run:

```json
{
  "e3": {
    "output_file": "proposal_ProjectName_better.docx",
    "project_name": "Aramco DMM7++ VSS",
    "section_count": 16,
    "ai_generated_count": 8,
    "gbb_tier": "better",
    "gbb_multiplier": 1.15,
    "total_price": 45885.0
  }
}
```

### E4 — written by `e4_routes.py`

Written under key `"e4"`.

```json
{
  "e4": {
    "project_name": "Aramco DMM7++ VSS",
    "total_questions": 47,
    "categories": ["Network Architecture", "Security", "Compliance", "Support"],
    "must_have_count": 22,
    "nice_to_have_count": 25,
    "output_file": "rfi_questionnaire_Aramco.xlsx"
  }
}
```

### E5 — not yet persisted to `step_outputs`

E5's route does **not** write to `step_outputs`. The coordinator must persist it.

Add key `"e5"` after a successful E5 run:

```json
{
  "e5": {
    "output_file": "design_ProjectName.docx",
    "project_name": "Aramco DMM7++ VSS",
    "hld_section_count": 6,
    "lld_section_count": 8,
    "generated_from": "e1",
    "total_sections": 14
  }
}
```

### Full `step_outputs` schema summary

| Key | Written by | When |
|---|---|---|
| `"1"` | E1 `/run` | After step 1 (file classifier) |
| `"2"` | E1 `/run` | After step 2 (missing docs) |
| `"3"` | E1 `/run` | After step 3 (requirements extractor) |
| `"4"` | E1 `/run` | After step 4 (legal trap flagger) |
| `"5"` | E1 `/run` | After step 5 (eval criteria extractor) |
| `"8"` | E1 `/checkpoint1/approve` | After step 8 (sector detector) |
| `"9"` | E1 `/checkpoint1/approve` | After step 9 (framework selector) |
| `"10"` | E1 `/checkpoint1/approve` | After step 10 (compliance matrix) |
| `"gaps"` | E1 `/checkpoint1/approve` | Gap analysis output |
| `"stats"` | E1 `/checkpoint1/approve` | Matrix statistics |
| `"xlsx_path"` | E1 `/checkpoint2/approve` | Absolute path to written XLSX |
| `"e2"` | E2 `/analyze` (or coordinator) | After E2 pipeline completes |
| `"e3"` | Coordinator (to be built) | After E3 pipeline completes |
| `"e4"` | E4 `/generate` (or coordinator) | After E4 pipeline completes |
| `"e5"` | Coordinator (to be built) | After E5 pipeline completes |
| `"checkpoints"` | Coordinator (to be built) | Checkpoint approvals/rejections log |

---

## 3. Checkpoint Contract for E2 / E3 / E4 / E5

E1 defines the pattern. Each engine checkpoint follows this contract.

### Pattern established by E1

- Engine runs deterministic steps, writes outputs to `step_outputs`
- `Opportunity.status` is set to `{engine}_pending` (waiting for engineer)
- Engineer reviews a UI page showing the engine's output
- `POST /api/{engine}/{id}/checkpoint/approve` — advances the pipeline
- `POST /api/{engine}/{id}/checkpoint/reject` — rejects with a reason, halts pipeline
- Revision (re-run with notes) is optional; E1 supports up to 3 loops

### E2 Checkpoint

**What the engineer reviews:**
- BoM match summary: matched SKUs, unmatched items, low-confidence items
- Pricing subtotal / total
- Output XLSX filename for download

**Actions:**
- Approve → sets `status = "e2_complete"`, coordinator triggers E3
- Reject → sets `status = "e2_rejected"`, logs reason to `step_outputs["checkpoints"]`
- Re-run → re-triggers E2 with optional notes injected (e.g., correct a vendor constraint)

**New endpoints to build:**

```
POST /api/e2/{opportunity_id}/checkpoint/approve
POST /api/e2/{opportunity_id}/checkpoint/reject
  body: { "reason": string }
```

**Guard condition:** `step_outputs["e2"]` must exist (E2 has run successfully).

**Status transition:** `e2_pending` → approve → `e2_complete` | reject → `e2_rejected`

### E3 Checkpoint

**What the engineer reviews:**
- Proposal section list with AI-generated vs template-filled counts
- GBB tier and total price
- Output DOCX filename for download and review

**Actions:**
- Approve → sets `status = "e3_complete"` (or `complete` if E3 is the last engine in the run)
- Reject → sets `status = "e3_rejected"`, logs reason
- Re-run → re-triggers E3 with a different `gbb_tier` or updated narrative notes

**New endpoints to build:**

```
POST /api/e3/{opportunity_id}/checkpoint/approve
POST /api/e3/{opportunity_id}/checkpoint/reject
  body: { "reason": string }
```

**Guard condition:** `step_outputs["e3"]` must exist.

**Status transition:** `e3_pending` → approve → `e3_complete` | reject → `e3_rejected`

### E4 Checkpoint

E4 (RFI questionnaire) is typically run before or in parallel with E2/E3, not after. It has no downstream dependency.

**What the engineer reviews:**
- Total questions generated, category breakdown
- Must-have vs nice-to-have split
- Output XLSX for download and review

**Actions:**
- Approve → sets `status = "e4_complete"`
- Reject → sets `status = "e4_rejected"`, logs reason
- Re-run not needed — E4 is fast and fully deterministic; just re-trigger

**New endpoints to build:**

```
POST /api/e4/{opportunity_id}/checkpoint/approve
POST /api/e4/{opportunity_id}/checkpoint/reject
  body: { "reason": string }
```

**Guard condition:** `step_outputs["e4"]` must exist.

### E5 Checkpoint

**What the engineer reviews:**
- HLD section count, LLD section count
- Whether generated from E1 data or blank
- Output DOCX for download and review

**Actions:**
- Approve → sets `status = "e5_complete"`
- Reject → sets `status = "e5_rejected"`, logs reason

**New endpoints to build:**

```
POST /api/e5/{opportunity_id}/checkpoint/approve
POST /api/e5/{opportunity_id}/checkpoint/reject
  body: { "reason": string }
```

**Guard condition:** `step_outputs["e5"]` must exist.

### Shared checkpoint utilities

Extract a shared helper (put in `app/api/checkpoint_utils.py`) used by all engine checkpoint routes:

```python
def get_opportunity_and_pipeline(opportunity_id: str, db: Session) -> tuple[Opportunity, PipelineState]:
    """Standard lookup — raises 404 if either record is missing."""
    ...

def log_checkpoint_event(
    pipeline: PipelineState,
    engine: str,          # "e2", "e3", etc.
    action: str,          # "approved", "rejected", "re_run"
    actor: str = "engineer",
    reason: str = "",
) -> None:
    """Append to step_outputs["checkpoints"] list."""
    entry = {
        "engine": engine,
        "action": action,
        "actor": actor,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    checkpoints = list(pipeline.step_outputs.get("checkpoints", []))
    checkpoints.append(entry)
    pipeline.step_outputs = {**pipeline.step_outputs, "checkpoints": checkpoints}
    flag_modified(pipeline, "step_outputs")
```

---

## 4. Pipeline Coordinator Design

### Purpose

A single endpoint that triggers an E1→E2→E3 run end-to-end, with status updates after each engine so the engineer can checkpoint between them. Replaces the current manual "call each engine separately" workflow.

### New model: `PipelineRun`

Add to `app/models/pipeline_run.py`:

```python
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("opportunities.id"))
    engines_requested: Mapped[list] = mapped_column(JSONB)   # ["e1", "e2", "e3"]
    engines_completed: Mapped[list] = mapped_column(JSONB, default=list)
    current_engine: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=...)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), ...)
```

This is optional for v1 — the coordinator can use `Opportunity.status` and `step_outputs` as state without a separate table. Add `PipelineRun` only if you need to support multiple concurrent run attempts or retry history.

### Coordinator endpoint

```
POST /api/coordinator/{opportunity_id}/run
```

**Request body:**

```json
{
  "engines": ["e2", "e3"],
  "gbb_tier": "better",
  "boq_filename": "BOQ_OP-2025-001.xlsx"
}
```

`engines` defaults to `["e2", "e3"]` if omitted. E1 is never triggered here — it has its own upload flow.

**Behavior (synchronous with long timeout, or background task):**

1. Validate: `Opportunity.status` must be `"e1_complete"` (or `"e2_complete"` if only E3 is requested).
2. For each engine in the requested list, in order:
   a. Set `Opportunity.status = "{engine}_running"`
   b. Call the engine's pipeline function directly (not via HTTP — import and call)
   c. On success: persist result to `step_outputs["{engine}"]`, set status to `"{engine}_pending"` (awaiting checkpoint)
   d. **Stop and return.** Do not auto-advance past a checkpoint.
3. Return current state.

**Checkpoint-gated flow:** The coordinator runs one engine at a time and stops at each checkpoint. The frontend polls `GET /api/e1/{id}/state` (or a new unified state endpoint) to detect `"{engine}_pending"` and render the checkpoint UI. Once the engineer approves, the frontend calls `POST /api/{engine}/{id}/checkpoint/approve`, which advances status to `"{engine}_complete"`. The coordinator is called again (or re-woken if async) to run the next engine.

**Alternative for v1 (simpler):** Do not build a long-running coordinator. Instead:
- The frontend calls `POST /api/e2/{id}/run` → gets result → shows checkpoint → engineer approves → calls `POST /api/e3/{id}/run` → etc.
- The coordinator is just a thin router that knows the engine order and which status unlocks which engine.

This is the recommended approach for v1. Build the full background-task coordinator only if the UI needs fire-and-forget behavior.

### One-click E1→E2→E3 frontend flow

```
User clicks "Run Full Pipeline"
  ↓
POST /api/v1/rfp/packages  (if not yet uploaded)
  ↓
POST /api/e1/{id}/run
  → status: checkpoint_1_pending
  → frontend renders Checkpoint 1 UI
Engineer approves
  ↓
POST /api/e1/{id}/checkpoint1/approve
  → status: checkpoint_2_pending
  → frontend renders Checkpoint 2 UI
Engineer approves
  ↓
POST /api/e1/{id}/checkpoint2/approve
  → status: e1_complete
  ↓
POST /api/e2/{id}/run  (coordinator triggers or user clicks)
  → status: e2_pending
  → frontend renders E2 Checkpoint UI
Engineer approves
  ↓
POST /api/e2/{id}/checkpoint/approve
  → status: e2_complete
  ↓
POST /api/e3/{id}/run
  → status: e3_pending
  → frontend renders E3 Checkpoint UI
Engineer approves
  ↓
POST /api/e3/{id}/checkpoint/approve
  → status: complete
```

### E2 run endpoint (to be built)

Currently E2 requires a BoQ file upload per request. For the coordinator flow, the BoQ file was already uploaded with the RFP package (it's a Document record). Add:

```
POST /api/e2/{opportunity_id}/run
```

This reads the BoQ file from `storage/{opportunity_id}/` (already on disk from the initial upload), reads RFP text from `Document.text_content`, runs `run_e2_pipeline`, and persists to `step_outputs["e2"]`. No file upload needed.

### E3 run endpoint (to be built)

```
POST /api/e3/{opportunity_id}/run
body: { "gbb_tier": "better" }
```

Reads from `step_outputs["e2"]` and `Document.text_content`, runs `run_e3_pipeline`, persists to `step_outputs["e3"]`, sets `status = "e3_pending"`.

### E5 run endpoint (to be built)

```
POST /api/e5/{opportunity_id}/run
```

Reads from `step_outputs` (E1 data), runs `run_e5_pipeline`, persists to `step_outputs["e5"]`, sets `status = "e5_pending"`.

---

## 5. Opportunities Dashboard API Spec

### Endpoints to build

All under `GET /api/v1/opportunities` prefix. Add to a new router: `app/api/opportunities_router.py`.

---

#### `GET /api/v1/opportunities`

List all opportunities with summary fields. Used for the dashboard table.

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | string | — | Filter by status value (e.g., `e1_complete`) |
| `client_name` | string | — | Partial match on client name (case-insensitive) |
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |
| `sort` | string | `created_at_desc` | Sort order: `created_at_desc`, `created_at_asc`, `updated_at_desc` |

**Response `200 OK`:**

```json
{
  "total": 47,
  "offset": 0,
  "limit": 50,
  "opportunities": [
    {
      "opportunity_id": "OP-2025-154381",
      "client_name": "Saudi Aramco",
      "project_name": "DMM7++ VSS",
      "status": "e1_complete",
      "pipeline_step": 12,
      "engines_completed": ["e1"],
      "created_at": "2025-11-01T09:23:00Z",
      "updated_at": "2025-11-03T14:45:00Z",
      "document_count": 16
    }
  ]
}
```

`engines_completed` is derived from `step_outputs` keys: if `"xlsx_path"` exists → E1 complete; if `"e2"` key exists → E2 complete; etc.

**Implementation note:** This requires a JOIN across `opportunities`, `pipeline_states`, and a COUNT on `documents`. Do it with a single SQLAlchemy query — do not N+1.

```python
from sqlalchemy import func

results = (
    db.query(
        Opportunity,
        PipelineState.current_step,
        PipelineState.step_outputs,
        func.count(Document.id).label("document_count"),
    )
    .outerjoin(PipelineState, PipelineState.opportunity_id == Opportunity.id)
    .outerjoin(Document, Document.opportunity_id == Opportunity.id)
    .group_by(Opportunity.id, PipelineState.current_step, PipelineState.step_outputs)
    .order_by(Opportunity.created_at.desc())
    .offset(offset)
    .limit(limit)
    .all()
)
```

---

#### `GET /api/v1/opportunities/{opportunity_id}`

Single opportunity detail. Used for the session detail page / pipeline status view.

**Response `200 OK`:**

```json
{
  "opportunity_id": "OP-2025-154381",
  "client_name": "Saudi Aramco",
  "project_name": "DMM7++ VSS",
  "status": "checkpoint_2_pending",
  "pipeline_step": 11,
  "engines_completed": ["e1"],
  "engines_available": ["e2", "e3", "e4", "e5"],
  "created_at": "2025-11-01T09:23:00Z",
  "updated_at": "2025-11-03T14:45:00Z",
  "documents": [
    {
      "filename": "Purchase_Requisition.docx",
      "file_format": "docx",
      "doc_type": "technical",
      "confidence": 0.95
    }
  ],
  "pipeline_summary": {
    "total_requirements": 42,
    "mandatory": 28,
    "sector": "oil_and_gas",
    "frameworks": ["NCA_ECC", "SACS-002", "ISO_27001"],
    "risk_flags": { "critical": 2, "high": 3, "medium": 4 }
  }
}
```

`pipeline_summary` is extracted from `step_outputs["stats"]` and `step_outputs["4"]`. Return `null` if E1 has not run yet.

`engines_available` is derived from status: after `e1_complete`, list `["e2", "e3", "e4", "e5"]`; after `e2_complete`, remove `"e2"`; etc.

---

#### `DELETE /api/v1/opportunities/{opportunity_id}`

Delete an opportunity and all associated records (documents, pipeline state, files on disk).

**Response `200 OK`:**

```json
{ "deleted": "OP-2025-154381" }
```

Use a transaction. Delete in order: `Documents` → `PipelineState` → `Opportunity` → files on disk (after DB commit, so a disk failure doesn't leave orphaned DB rows).

---

#### `PATCH /api/v1/opportunities/{opportunity_id}`

Update metadata fields only. Does not affect pipeline state.

**Request body (all optional):**

```json
{
  "client_name": "Saudi Aramco",
  "project_name": "DMM7++ VSS — Updated Scope"
}
```

**Response `200 OK`:** Updated opportunity object (same shape as GET detail, minus deep fields).

---

### Register the router

In `app/main.py`, add:

```python
from app.api.opportunities_router import router as opportunities_router
app.include_router(opportunities_router, prefix="/api/v1")
```

---

## 6. Implementation Order

Build in this sequence to minimize rework:

1. **Fix E1 status bug** — change `"complete"` → `"e1_complete"` in `checkpoint2_approve`. One-line change.

2. **Opportunities dashboard endpoints** — `GET /api/v1/opportunities` and `GET /api/v1/opportunities/{id}`. Pure read path, no engine logic, immediately useful for the frontend.

3. **Shared checkpoint utilities** — `app/api/checkpoint_utils.py` with `get_opportunity_and_pipeline` and `log_checkpoint_event`. Needed by steps 4 and 5.

4. **E2 checkpoint endpoints** — `POST /api/e2/{id}/checkpoint/approve` and `/reject`. Also add `POST /api/e2/{id}/run` (reads BoQ from disk, no file upload).

5. **E3 run + checkpoint endpoints** — `POST /api/e3/{id}/run` and `/checkpoint/approve` and `/reject`. Write result to `step_outputs["e3"]`.

6. **E4 checkpoint endpoints** — `POST /api/e4/{id}/checkpoint/approve` and `/reject`. E4 already writes to `step_outputs["e4"]` — just add the approve/reject gates.

7. **E5 run + checkpoint endpoints** — `POST /api/e5/{id}/run` (persist to `step_outputs["e5"]`) and `/checkpoint/approve` and `/reject`.

8. **`DELETE` and `PATCH` on opportunities** — housekeeping endpoints, low risk.

9. **Frontend pipeline coordinator** — the frontend calls engines in sequence based on status polling; no backend coordinator service needed for v1.
