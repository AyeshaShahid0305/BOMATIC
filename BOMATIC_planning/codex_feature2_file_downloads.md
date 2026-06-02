# Codex Task: Feature 2 — File Download Endpoints + UI Download Buttons

## Context

BOMATIC is a FastAPI + Next.js + PostgreSQL pre-sales platform. All 5 engines (E1–E5) are
complete and write output files to disk, but there is no generic download endpoint. The
`DownloadButton` component at `frontend/app/components/DownloadButton.tsx` already calls
`/api/v1/rfp/packages/{opportunity_id}/outputs/{filename}` — but this route does not exist.
E2 and E3 pages already render `DownloadButton` but it always 404s. E1 and E5 have no
download UI at all. This task adds the missing backend route and the missing frontend pages.

---

## Step 1 — Read these files first (in this order)

Read every file completely before writing any code.

1. `backend/app/routers/rfp.py`
2. `backend/app/config.py`
3. `backend/app/models/opportunity.py`
4. `backend/app/models/pipeline_state.py`
5. `backend/app/api/e1_router.py`
6. `backend/app/api/e2_routes.py`
7. `backend/app/api/e3_routes.py`
8. `backend/app/api/e5_routes.py`
9. `frontend/app/components/DownloadButton.tsx`
10. `frontend/app/e2/[id]/page.tsx`
11. `frontend/app/e3/[id]/review/page.tsx`
12. `frontend/app/e5/page.tsx`
13. `frontend/next.config.mjs`

---

## Step 2 — Understand the current file locations

Before writing any code, understand where each engine writes its output files:

- **E1** — writes `compliance_matrix_{opportunity_id}.xlsx` to `storage/{opportunity_id}/`.
  The absolute path is stored in `pipeline_state.step_outputs["xlsx_path"]`.

- **E2** — writes its output Excel to `backend/app/engines/e2/output/`.
  The filename (basename only) is stored in `pipeline_state.step_outputs["e2"]["output_file"]`.

- **E3** — writes its output DOCX to `backend/app/engines/e3/output/`.
  The filename (basename only) is stored in `pipeline_state.step_outputs["e3"]["output_file"]`.

- **E5** — writes its output DOCX to `backend/app/engines/e5/output/`.
  The filename (basename only) is stored in `pipeline_state.step_outputs["e5"]["output_file"]`.

The frontend's `DownloadButton` uses logical filenames (e.g. `bom_workbook.xlsx`,
`technical_proposal.docx`). The backend must map logical filenames to actual file paths
using `step_outputs`.

---

## Step 3 — Backend changes

### 3A. Add two new routes to `backend/app/routers/rfp.py`

Add the following imports at the top of `rfp.py` (after the existing imports):

```python
from pathlib import Path
from fastapi.responses import FileResponse
```

Then add these two route functions at the bottom of `rfp.py`, after the existing
`get_rfp_package` function. Do not modify any existing function.

---

#### Route 1: `GET /rfp/packages/{opportunity_id}/outputs`

Function name: `list_outputs`

Logic:
1. Query `Opportunity` by `opportunity_id`. Return 404 if not found.
2. Query `PipelineState` by `opportunity.id`. Return 404 if not found.
3. Read `step_outputs` from the pipeline state (default to `{}`).
4. Build a list of available output dicts. For each item in the list below, include it
   only if the corresponding key exists and is non-empty in `step_outputs`:

   | logical_name              | engine | ready condition                                    |
   |---------------------------|--------|----------------------------------------------------|
   | `compliance_matrix.xlsx`  | E1     | `step_outputs.get("xlsx_path")` is truthy          |
   | `bom_workbook.xlsx`       | E2     | `step_outputs.get("e2", {}).get("output_file")`    |
   | `technical_proposal.docx` | E3     | `step_outputs.get("e3", {}).get("output_file")`    |
   | `hld_lld.docx`            | E5     | `step_outputs.get("e5", {}).get("output_file")`    |

5. Return:
```json
{
  "opportunity_id": "<opportunity_id>",
  "outputs": [
    { "filename": "compliance_matrix.xlsx", "engine": "E1" },
    { "filename": "bom_workbook.xlsx", "engine": "E2" }
  ]
}
```

---

#### Route 2: `GET /rfp/packages/{opportunity_id}/outputs/{filename}`

Function name: `download_output`

Parameters: `opportunity_id: str`, `filename: str`

Logic:
1. **Path traversal guard**: if `filename` contains `/` or `..`, raise `HTTPException(400,
   "Invalid filename.")`.
2. Query `Opportunity` by `opportunity_id`. Return 404 if not found.
3. Query `PipelineState` by `opportunity.id`. Return 404 if not found.
4. Read `step_outputs` from the pipeline state (default to `{}`).
5. Resolve the actual file path using this mapping:

```python
settings = get_settings()

# Base dirs — derive from __file__ so they work regardless of cwd
_ENGINES_DIR = Path(__file__).parent.parent / "app" / "engines"
# Note: rfp.py is at backend/app/routers/rfp.py, so:
# Path(__file__).parent = backend/app/routers
# Path(__file__).parent.parent = backend/app
# Path(__file__).parent.parent / "engines" = backend/app/engines

if filename == "compliance_matrix.xlsx":
    raw = step_outputs.get("xlsx_path", "")
    if not raw:
        raise HTTPException(404, "E1 compliance matrix not yet generated.")
    file_path = Path(raw)

elif filename == "bom_workbook.xlsx":
    actual = (step_outputs.get("e2") or {}).get("output_file", "")
    if not actual:
        raise HTTPException(404, "E2 BoM workbook not yet generated.")
    file_path = Path(__file__).parent.parent / "engines" / "e2" / "output" / Path(actual).name

elif filename == "technical_proposal.docx":
    actual = (step_outputs.get("e3") or {}).get("output_file", "")
    if not actual:
        raise HTTPException(404, "E3 technical proposal not yet generated.")
    file_path = Path(__file__).parent.parent / "engines" / "e3" / "output" / Path(actual).name

elif filename == "hld_lld.docx":
    actual = (step_outputs.get("e5") or {}).get("output_file", "")
    if not actual:
        raise HTTPException(404, "E5 HLD/LLD document not yet generated.")
    file_path = Path(__file__).parent.parent / "engines" / "e5" / "output" / Path(actual).name

else:
    raise HTTPException(404, f"Unknown output file '{filename}'.")
```

6. If `file_path` does not exist on disk: raise `HTTPException(404, "File not found on disk.")`.
7. Resolve the MIME type:
   - `.xlsx` → `"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`
   - `.docx` → `"application/vnd.openxmlformats-officedocument.wordprocessingml.document"`
   - `.pdf` → `"application/pdf"`
   - anything else → `"application/octet-stream"`
8. Return `FileResponse(path=str(file_path), media_type=mime, filename=filename)`.
   Use the `filename` keyword arg so the `Content-Disposition` header uses the logical name,
   not the engine-generated name.

**Important**: `rfp.py` is mounted under `/api/v1` in `main.py`, so these routes will be
reachable at:
- `GET /api/v1/rfp/packages/{opportunity_id}/outputs`
- `GET /api/v1/rfp/packages/{opportunity_id}/outputs/{filename}`

The Next.js rewrite in `next.config.mjs` proxies `/api/:path*` →
`http://localhost:8000/api/:path*`, so the frontend `fetch` calls
`/api/v1/rfp/packages/{id}/outputs/{filename}` will reach the backend correctly.

---

### 3B. Compute `_ENGINES_DIR` path correctly

`rfp.py` lives at `backend/app/routers/rfp.py`.
- `Path(__file__).parent` = `backend/app/routers/`
- `Path(__file__).parent.parent` = `backend/app/`
- `Path(__file__).parent.parent / "engines" / "e2" / "output"` = `backend/app/engines/e2/output/`

Verify this is correct by checking the result of:
```
ls backend/app/engines/e2/output/
ls backend/app/engines/e3/output/
ls backend/app/engines/e5/output/
```
If those directories do not exist, create them:
```python
# At module level in rfp.py, after imports:
for _d in ["e2", "e3", "e5"]:
    (Path(__file__).parent.parent / "engines" / _d / "output").mkdir(parents=True, exist_ok=True)
```

---

## Step 4 — Frontend changes

### 4A. Create `frontend/app/e1/[id]/complete/page.tsx`

This page is shown after E1 completes (status = `e1_complete`, `current_step >= 12`).
Model it exactly on `frontend/app/e3/[id]/review/page.tsx` — same structure, same patterns.

Differences from E3 review page:
- Page title: `"E1 Compliance Matrix"`
- Description below title: `"Opportunity {id}"`
- Ready condition: `(state?.pipeline_step ?? 0) >= 12`
- Not-ready warning text: `"E1 is not complete yet. Run the E1 pipeline before downloading."`
  Link text: `"Open E1 Upload"` → `href="/e1/upload"`
- Downloads section heading: `"Downloads"`
- One download button:
  ```tsx
  <DownloadButton
    opportunityId={id}
    filename="compliance_matrix.xlsx"
    label="Download Compliance Matrix"
  />
  ```
- Breadcrumb: BOMATIC / Opportunities / E1 Complete

Import `DownloadButton` from `"@/app/components/DownloadButton"`.
Use `useParams<{ id: string }>()` from `"next/navigation"` to get `id`.
Fetch opportunity state from `GET /api/v1/rfp/packages/{id}`.

---

### 4B. Create `frontend/app/e5/[id]/page.tsx`

This page is shown after E5 completes (status = `e5_complete`, `current_step >= 21`).
Model it exactly on `frontend/app/e3/[id]/review/page.tsx`.

Differences:
- Page title: `"E5 HLD/LLD Design"`
- Description: `"Opportunity {id}"`
- Ready condition: `(state?.pipeline_step ?? 0) >= 21`
- Not-ready warning: `"E5 is not complete yet. Generate the design document first."`
  Link text: `"Open Design Generator"` → `href={`/e5?session_id=${encodeURIComponent(id)}`}`
- Downloads section heading: `"Downloads"`
- One download button:
  ```tsx
  <DownloadButton
    opportunityId={id}
    filename="hld_lld.docx"
    label="Download HLD/LLD Document"
  />
  ```
- Breadcrumb: BOMATIC / Opportunities / E5 Design

Create the directory `frontend/app/e5/[id]/` and put `page.tsx` inside it.

---

### 4C. Do NOT modify these files

Do not modify any of the following — they already work correctly:
- `frontend/app/components/DownloadButton.tsx`
- `frontend/app/e2/[id]/page.tsx`
- `frontend/app/e3/[id]/review/page.tsx`
- `frontend/app/e3/[id]/page.tsx` (re-exports review page)

---

## Step 5 — Validation steps

Run each check in order. Fix any failure before moving to the next.

### 5A. Backend syntax check
```bash
cd backend
python -m py_compile app/routers/rfp.py
echo "rfp.py syntax OK"
```

### 5B. Backend import check
```bash
cd backend
python -c "from app.routers.rfp import list_outputs, download_output; print('imports OK')"
```
If this fails, check that `FileResponse` and `Path` are imported in `rfp.py`.

### 5C. TypeScript check for new frontend files
```bash
cd frontend
npx tsc --noEmit
```
Fix any type errors before continuing.

### 5D. Start the backend and run curl tests

Start the backend (or assume it is already running on port 8000 with a valid `BOMATIC_API_KEY`).
Substitute `<API_KEY>` with the value from `backend/.env`.
Substitute `<OPP_ID>` with an opportunity ID that exists in your database.

**Test 1 — List outputs for a new (not yet run) opportunity. Should return empty list.**
```bash
curl -s -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs | python -m json.tool
```
Expected: `{"opportunity_id": "<OPP_ID>", "outputs": []}`

**Test 2 — Download a file that doesn't exist yet. Should return 404.**
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs/compliance_matrix.xlsx
```
Expected: `404`

**Test 3 — Path traversal blocked. Should return 400.**
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: <API_KEY>" \
  "http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs/..%2F..%2Fetc%2Fpasswd"
```
Expected: `400`

**Test 4 — Unknown logical filename. Should return 404.**
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs/random_file.txt
```
Expected: `404`

**Test 5 — After E1 completes on an opportunity, the matrix should be downloadable.**

Run E1 on an opportunity if needed:
```bash
curl -s -X POST -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/run | python -m json.tool
# (run checkpoint1 and checkpoint2 approve as well to generate the xlsx)
```

Then:
```bash
curl -s -I -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs/compliance_matrix.xlsx
```
Expected: HTTP 200 with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
and `Content-Disposition: attachment; filename="compliance_matrix.xlsx"`

### 5E. Check new frontend pages render without errors
```bash
cd frontend
npm run build 2>&1 | grep -E "error|Error|warning"
```
Expected: zero TypeScript or build errors for the two new pages.

### 5F. Verify file structure
```bash
ls frontend/app/e1/[id]/complete/page.tsx
ls frontend/app/e5/[id]/page.tsx
```
Both files must exist.

### 5G. Verify DownloadButton URL is unchanged
```bash
grep -n "outputs" frontend/app/components/DownloadButton.tsx
```
Expected: the URL pattern `/api/v1/rfp/packages/${...}/outputs/${...}` is present and unchanged.

---

## Step 6 — Summary of files changed

| Action   | File path                                      |
|----------|------------------------------------------------|
| Modified | `backend/app/routers/rfp.py`                   |
| Created  | `frontend/app/e1/[id]/complete/page.tsx`       |
| Created  | `frontend/app/e5/[id]/page.tsx`                |

No other files should be modified.

---

## Step 7 — Git commit message

```
feat: add generic file download endpoints and E1/E5 download pages

Backend (rfp.py):
- GET /api/v1/rfp/packages/{id}/outputs — list available engine outputs
- GET /api/v1/rfp/packages/{id}/outputs/{filename} — stream file download
  Logical filenames: compliance_matrix.xlsx (E1), bom_workbook.xlsx (E2),
  technical_proposal.docx (E3), hld_lld.docx (E5)
  Resolves actual paths from pipeline_state.step_outputs
  Blocks path traversal; returns 404 for ungenerated/unknown files

Frontend:
- frontend/app/e1/[id]/complete/page.tsx — E1 complete page with
  compliance_matrix.xlsx DownloadButton
- frontend/app/e5/[id]/page.tsx — E5 review page with
  hld_lld.docx DownloadButton

E2 and E3 download pages already existed and now work end-to-end.
```
