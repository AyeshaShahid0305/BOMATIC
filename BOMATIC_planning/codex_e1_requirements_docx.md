# Codex Task: E1 Requirements DOCX Output

## Context

BOMATIC is a FastAPI + Next.js + PostgreSQL pre-sales platform. After E1 completes,
engineers can download the compliance matrix XLSX. A requirements baseline DOCX
should also be available — a clean Word document listing all extracted requirements
grouped by classification. The E1 complete page already has one DownloadButton
(compliance_matrix.xlsx); this task adds a second one (requirements.docx).

**What to build:**
1. `backend/app/engines/e1/step13_requirements_docx_writer.py` — writes the DOCX
   to `storage/{opportunity_id}/` using python-docx.
2. `backend/app/api/e1_router.py` — call it inside `checkpoint2_approve`, store
   the absolute path in `step_outputs["requirements_docx_path"]`.
3. `backend/app/routers/rfp.py` — add `requirements.docx` to `_collect_outputs`
   and `_resolve_output_path` (same pattern as `compliance_matrix.xlsx`).
4. `frontend/app/e1/[id]/complete/page.tsx` — add a second DownloadButton.

**DOCX format:**
- Title: `Requirements Baseline — {project_name}`
- Subtitle: `Generated {date}  |  {N} requirements`
- Three sections: Mandatory, Optional, Conditional (skip section if count = 0)
- Each requirement: numbered list item with text, then a small grey line showing
  `ID: {req_id}  |  Confidence: {pct}%  |  Source: {source_file}`
- Font: Calibri 11pt body, 14pt section headings, 20pt title

**Storage:** save to `storage/{opportunity_id}/requirements_{opportunity_id}.docx`
(same directory as the compliance matrix XLSX). Store the absolute path string in
`step_outputs["requirements_docx_path"]`.

---

## Step 1 — Read these files first (in this order)

1. `backend/app/engines/e1/step12_xlsx_writer.py` — understand the output dir pattern
2. `backend/app/api/e1_router.py` — see `checkpoint2_approve` and where xlsx_path is stored
3. `backend/app/routers/rfp.py` — see `_collect_outputs` and `_resolve_output_path`
4. `frontend/app/e1/[id]/complete/page.tsx` — see existing DownloadButton

---

## Step 2 — Create `backend/app/engines/e1/step13_requirements_docx_writer.py`

Create this file with exactly this content:

```python
"""
step13_requirements_docx_writer

Writes a requirements baseline Word document (.docx) from the list of
extracted requirements stored in step_outputs["3"].

Usage:
    from app.engines.e1.step13_requirements_docx_writer import write_requirements_docx

    docx_path = write_requirements_docx(
        requirements=pipeline.step_outputs["3"],
        opportunity_id=opportunity_id,
        project_name=opportunity.project_name or opportunity_id,
        output_dir=Path(settings.upload_dir) / opportunity_id,
    )
    # docx_path is an absolute Path; store str(docx_path) in step_outputs
"""

from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

_FONT = "Calibri"
_TITLE_SIZE = Pt(20)
_SUBTITLE_SIZE = Pt(10)
_HEADING_SIZE = Pt(14)
_BODY_SIZE = Pt(11)
_META_SIZE = Pt(9)
_HEADING_COLOR = RGBColor(0x1F, 0x38, 0x64)   # dark navy
_META_COLOR = RGBColor(0x75, 0x75, 0x75)       # grey


def _run(para, text: str, size: Pt, bold: bool = False,
         color: RGBColor | None = None, italic: bool = False):
    run = para.add_run(text)
    run.font.name = _FONT
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = color
    return run


def write_requirements_docx(
    requirements: list[dict],
    opportunity_id: str,
    project_name: str,
    output_dir: Path,
) -> Path:
    """
    Write a requirements baseline DOCX and return its path.

    Args:
        requirements:   list of requirement dicts from step_outputs["3"].
                        Expected keys: id, text, classification, confidence,
                        source_file (all optional — falls back gracefully).
        opportunity_id: used in the output filename.
        project_name:   shown in the document title.
        output_dir:     directory where the file is saved (created if missing).

    Returns:
        Absolute Path to the generated .docx file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"requirements_{opportunity_id}.docx"

    doc = Document()

    # Set default Normal style
    normal = doc.styles["Normal"]
    normal.font.name = _FONT
    normal.font.size = _BODY_SIZE

    # ── Title ──────────────────────────────────────────────────────────────
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _run(title_para, "Requirements Baseline", _TITLE_SIZE, bold=True, color=_HEADING_COLOR)

    sub_para = doc.add_paragraph()
    sub_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    _run(
        sub_para,
        f"{project_name}  |  Generated {date_str}  |  {len(requirements)} requirement(s)",
        _SUBTITLE_SIZE,
        color=_META_COLOR,
    )

    doc.add_paragraph()  # spacer

    # ── Group by classification ────────────────────────────────────────────
    order = ["mandatory", "optional", "conditional"]
    groups: dict[str, list[dict]] = {k: [] for k in order}
    other: list[dict] = []

    for req in requirements:
        cls = str(req.get("classification") or "").lower()
        if cls in groups:
            groups[cls].append(req)
        else:
            other.append(req)

    if other:
        groups["other"] = other
        order.append("other")

    # ── Write each section ─────────────────────────────────────────────────
    for cls in order:
        reqs = groups.get(cls, [])
        if not reqs:
            continue

        # Section heading
        heading_para = doc.add_paragraph()
        _run(
            heading_para,
            f"{cls.capitalize()} ({len(reqs)})",
            _HEADING_SIZE,
            bold=True,
            color=_HEADING_COLOR,
        )

        # Requirement items
        for i, req in enumerate(reqs, start=1):
            text = str(req.get("text") or req.get("description") or "").strip()
            req_id = str(req.get("id") or req.get("req_id") or f"{cls[:3].upper()}-{i:03d}")
            confidence = req.get("confidence")
            source = str(req.get("source_file") or req.get("source") or "")

            # Main text
            body_para = doc.add_paragraph(style="List Number")
            _run(body_para, text if text else "(no text)", _BODY_SIZE)

            # Meta line
            meta_parts = [f"ID: {req_id}"]
            if confidence is not None:
                meta_parts.append(f"Confidence: {float(confidence) * 100:.0f}%")
            if source:
                meta_parts.append(f"Source: {source}")

            meta_para = doc.add_paragraph()
            meta_para.paragraph_format.left_indent = Pt(18)
            meta_para.paragraph_format.space_after = Pt(4)
            _run(meta_para, "  |  ".join(meta_parts), _META_SIZE, color=_META_COLOR, italic=True)

        doc.add_paragraph()  # section spacer

    doc.save(out_path)
    return out_path
```

---

## Step 3 — Update `backend/app/api/e1_router.py`

Make two targeted changes inside `checkpoint2_approve`. Do not modify any other function.

**Change 1 — Add import at the top of the file**, after the existing engine imports:
```python
from app.engines.e1.step13_requirements_docx_writer import write_requirements_docx
```

**Change 2 — Call `write_requirements_docx` inside `checkpoint2_approve`**, immediately
after `xlsx_path` is assigned and before `db.commit()`.

Find this block in `checkpoint2_approve`:
```python
    xlsx_path = await asyncio.get_running_loop().run_in_executor(
        None,
        functools.partial(
            write_compliance_matrix_xlsx,
            matrix_rows=matrix_rows,
            gaps=gaps,
            stats=stats,
            opportunity_id=opportunity_id,
            output_dir=output_dir,
        ),
    )

    pipeline.step_outputs = {
        **pipeline.step_outputs,
        "xlsx_path": str(xlsx_path),
    }
    pipeline.current_step = 12
    opportunity.status = "e1_complete"
    db.commit()
```

Replace with:
```python
    xlsx_path = await asyncio.get_running_loop().run_in_executor(
        None,
        functools.partial(
            write_compliance_matrix_xlsx,
            matrix_rows=matrix_rows,
            gaps=gaps,
            stats=stats,
            opportunity_id=opportunity_id,
            output_dir=output_dir,
        ),
    )

    # Generate requirements baseline DOCX alongside the compliance matrix
    requirements: list[dict] = pipeline.step_outputs.get("3", [])
    requirements_docx_path = write_requirements_docx(
        requirements=requirements,
        opportunity_id=opportunity_id,
        project_name=opportunity.project_name or opportunity_id,
        output_dir=output_dir,
    )

    pipeline.step_outputs = {
        **pipeline.step_outputs,
        "xlsx_path": str(xlsx_path),
        "requirements_docx_path": str(requirements_docx_path),
    }
    pipeline.current_step = 12
    opportunity.status = "e1_complete"
    db.commit()
```

---

## Step 4 — Update `backend/app/routers/rfp.py`

Make two targeted changes. Do not modify any other function.

### 4A. `_collect_outputs`

Find the block that handles the E1 compliance matrix:
```python
    xlsx_path = outputs.get("xlsx_path")
    if xlsx_path:
        add_file("E1", "Compliance Matrix", "compliance_matrix.xlsx", Path(xlsx_path))
```

Add the requirements DOCX immediately after it:
```python
    xlsx_path = outputs.get("xlsx_path")
    if xlsx_path:
        add_file("E1", "Compliance Matrix", "compliance_matrix.xlsx", Path(xlsx_path))

    req_docx_path = outputs.get("requirements_docx_path")
    if req_docx_path:
        add_file("E1", "Requirements Baseline", "requirements.docx", Path(req_docx_path))
```

### 4B. `_resolve_output_path`

Find the block that handles `compliance_matrix.xlsx`:
```python
    xlsx_path = outputs.get("xlsx_path")
    if xlsx_path:
        path = Path(xlsx_path)
        candidates["compliance_matrix.xlsx"] = path
        candidates[path.name] = path
```

Add the requirements DOCX immediately after it:
```python
    xlsx_path = outputs.get("xlsx_path")
    if xlsx_path:
        path = Path(xlsx_path)
        candidates["compliance_matrix.xlsx"] = path
        candidates[path.name] = path

    req_docx_path = outputs.get("requirements_docx_path")
    if req_docx_path:
        path = Path(req_docx_path)
        candidates["requirements.docx"] = path
        candidates[path.name] = path
```

---

## Step 5 — Update `frontend/app/e1/[id]/complete/page.tsx`

Make one targeted change. Find the downloads grid:
```tsx
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <DownloadButton
                opportunityId={id}
                filename="compliance_matrix.xlsx"
                label="Download Compliance Matrix"
              />
            </div>
```

Replace with:
```tsx
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <DownloadButton
                opportunityId={id}
                filename="compliance_matrix.xlsx"
                label="Download Compliance Matrix"
              />
              <DownloadButton
                opportunityId={id}
                filename="requirements.docx"
                label="Download Requirements Baseline"
              />
            </div>
```

---

## Step 6 — Validation steps

### 6A. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e1/step13_requirements_docx_writer.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e1_router.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/routers/rfp.py
```
Expected: no output.

### 6B. Import check
```
backend\.venv\Scripts\python.exe -c "
from app.engines.e1.step13_requirements_docx_writer import write_requirements_docx
from app.api.e1_router import checkpoint2_approve
print('imports OK')
"
```
Expected: `imports OK`

### 6C. Unit test the DOCX writer with mock data
```
backend\.venv\Scripts\python.exe -c "
import tempfile
from pathlib import Path
from app.engines.e1.step13_requirements_docx_writer import write_requirements_docx
from docx import Document

reqs = [
    {'id': 'REQ-001', 'text': 'The vendor shall supply Cisco ASA 5516-X firewalls.', 'classification': 'mandatory', 'confidence': 0.95, 'source_file': 'rfp.pdf'},
    {'id': 'REQ-002', 'text': 'Optional 10G uplinks preferred.', 'classification': 'optional', 'confidence': 0.80, 'source_file': 'rfp.pdf'},
    {'id': 'REQ-003', 'text': 'PoE+ required if IP phones are deployed.', 'classification': 'conditional', 'confidence': 0.75, 'source_file': 'addendum.pdf'},
]

with tempfile.TemporaryDirectory() as tmp:
    out = write_requirements_docx(reqs, 'TEST-001', 'Riyadh Campus Network', Path(tmp))
    assert out.exists(), 'File not created'
    assert out.name == 'requirements_TEST-001.docx'
    doc = Document(out)
    full_text = ' '.join(p.text for p in doc.paragraphs)
    assert 'Requirements Baseline' in full_text, 'Missing title'
    assert 'Mandatory' in full_text, 'Missing Mandatory section'
    assert 'REQ-001' in full_text, 'Missing requirement ID'
    print('All assertions passed.')
"
```
Expected: `All assertions passed.`

### 6D. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 6E. Frontend build
```
cd frontend && npm run build
```
Expected: zero errors. Both DownloadButtons visible in the E1 complete page output.

### 6F. Integration test

Run E1 on an existing opportunity through to checkpoint2 approval, then check:
```
curl -s -H "X-API-Key: bomatic-dev-key" ^
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs | python -m json.tool
```
Expected: both `compliance_matrix.xlsx` and `requirements.docx` appear in the outputs
array, both with `"engine": "E1"`.

---

## Step 7 — Summary of files changed

| Action   | File path                                                    |
|----------|--------------------------------------------------------------|
| Created  | `backend/app/engines/e1/step13_requirements_docx_writer.py` |
| Modified | `backend/app/api/e1_router.py`                               |
| Modified | `backend/app/routers/rfp.py`                                 |
| Modified | `frontend/app/e1/[id]/complete/page.tsx`                     |

No DB migration. No new dependencies (python-docx already in requirements.txt).

---

## Step 8 — Git commit message

```
feat: add E1 requirements baseline DOCX output

- step13_requirements_docx_writer.py: write_requirements_docx()
  Generates a Word document grouping requirements by classification
  (Mandatory / Optional / Conditional). Each item shows text, ID,
  confidence %, and source file. Saved to storage/{opportunity_id}/.

- e1_router.py: call write_requirements_docx in checkpoint2_approve
  alongside the compliance matrix XLSX; store absolute path in
  step_outputs["requirements_docx_path"]

- rfp.py: extend _collect_outputs and _resolve_output_path to map
  "requirements.docx" to the stored path (same pattern as xlsx_path)

- e1/[id]/complete/page.tsx: add second DownloadButton for
  requirements.docx alongside the existing compliance matrix button
```
