# Codex Task: E3 PDF Generation (submission.pdf)

## Context

BOMATIC is a FastAPI + Next.js + PostgreSQL pre-sales platform. E3 generates a
technical proposal DOCX (`technical_proposal.docx`) and stores it in
`backend/app/engines/e3/output/`. The E3 review page already renders a
`DownloadButton` for `submission.pdf`, but that button always 404s because the
PDF is never created.

This task adds PDF conversion: after the DOCX is written, convert it to PDF using
LibreOffice headless subprocess. The PDF is saved alongside the DOCX in the same
output directory. Its filename is stored in `step_outputs["e3"]["pdf_file"]`. The
existing `_collect_outputs` and `_resolve_output_path` functions in `rfp.py` are
extended to serve `submission.pdf` through the generic download endpoint.

Conversion is best-effort. If LibreOffice is not found, conversion is skipped
silently — the DOCX download still works, only the PDF is unavailable.

---

## Step 1 — Read these files first (in this order)

Read every file completely before writing any code.

1. `backend/app/engines/e3/pipeline.py`
2. `backend/app/engines/e3/step6_docx_writer.py`
3. `backend/app/api/e3_routes.py`
4. `backend/app/routers/rfp.py`
5. `frontend/app/e3/[id]/review/page.tsx`

---

## Step 2 — Create `backend/app/engines/e3/step7_pdf_converter.py`

Create this file with exactly this content:

```python
"""
step7_pdf_converter — convert a DOCX to PDF using LibreOffice headless.

Usage:
    from app.engines.e3.step7_pdf_converter import convert_docx_to_pdf

    pdf_path = convert_docx_to_pdf(docx_path, output_dir)
    if pdf_path is None:
        # LibreOffice not found or conversion failed — handle gracefully
        ...

Returns the Path of the generated PDF, or None on any failure.
Never raises — all exceptions are caught and logged.
"""

import shutil
import subprocess
from pathlib import Path

# Common LibreOffice executable paths across platforms
_SOFFICE_CANDIDATES = [
    "soffice",                                              # on PATH (Linux/Mac)
    "libreoffice",                                          # on PATH (Linux)
    r"C:\Program Files\LibreOffice\program\soffice.exe",   # Windows default
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",  # Windows 32-bit
    "/usr/bin/libreoffice",                                 # Linux absolute
    "/usr/bin/soffice",                                     # Linux absolute alt
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",# macOS
]


def _find_soffice() -> str | None:
    """Return the first usable LibreOffice executable path, or None."""
    for candidate in _SOFFICE_CANDIDATES:
        # shutil.which handles PATH lookup; Path.exists handles absolute paths
        found = shutil.which(candidate) or (Path(candidate).exists() and candidate)
        if found:
            return str(found)
    return None


def convert_docx_to_pdf(docx_path: Path, output_dir: Path) -> Path | None:
    """
    Convert docx_path to PDF in output_dir using LibreOffice headless.

    Args:
        docx_path:  Absolute path to the source .docx file.
        output_dir: Directory where the .pdf will be written.
                    LibreOffice names the output {docx_path.stem}.pdf.

    Returns:
        Path to the generated PDF, or None if conversion failed or
        LibreOffice is not available.
    """
    soffice = _find_soffice()
    if not soffice:
        print("PDF conversion skipped: LibreOffice not found.")
        return None

    if not docx_path.exists():
        print(f"PDF conversion skipped: source file not found: {docx_path}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(docx_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,  # 2-minute timeout
        )

        if result.returncode != 0:
            print(
                f"LibreOffice conversion failed (exit {result.returncode}). "
                f"stderr: {result.stderr.strip()}"
            )
            return None

        pdf_path = output_dir / (docx_path.stem + ".pdf")
        if not pdf_path.exists():
            print(f"PDF conversion: LibreOffice reported success but output not found at {pdf_path}")
            return None

        return pdf_path

    except subprocess.TimeoutExpired:
        print("PDF conversion timed out after 120 seconds.")
        return None
    except Exception as exc:
        print(f"PDF conversion error ({type(exc).__name__}): {exc}")
        return None
```

---

## Step 3 — Update `backend/app/engines/e3/pipeline.py`

Make one targeted change only. Do not modify any other function.

**Add the import** at the top of the file, after the existing imports:
```python
from .step7_pdf_converter import convert_docx_to_pdf
```

**Extend `run_e3_pipeline`** to call the converter after `write_proposal`.

Find this block at the end of `run_e3_pipeline`:
```python
    output_path = write_proposal(assembled, e1_data["project_name"], gbb_tier)

    return {
        "output_file": output_path.name,
        "project_name": e1_data["project_name"],
        "section_count": len(assembled),
        "ai_generated_count": sum(1 for s in assembled if s["ai_generated"]),
        "gbb_tier": gbb_tier,
        "gbb_multiplier": gbb_result.multiplier,
        "total_price": gbb_result.adjusted_price,
    }
```

Replace it with:
```python
    output_path = write_proposal(assembled, e1_data["project_name"], gbb_tier)

    # Convert DOCX to PDF (best-effort — None if LibreOffice unavailable)
    pdf_path = convert_docx_to_pdf(output_path, output_path.parent)

    return {
        "output_file": output_path.name,
        "pdf_file": pdf_path.name if pdf_path else None,
        "project_name": e1_data["project_name"],
        "section_count": len(assembled),
        "ai_generated_count": sum(1 for s in assembled if s["ai_generated"]),
        "gbb_tier": gbb_tier,
        "gbb_multiplier": gbb_result.multiplier,
        "total_price": gbb_result.adjusted_price,
    }
```

---

## Step 4 — Update `backend/app/api/e3_routes.py`

Make one targeted change in the `generate_proposal` route.

Find the block that writes to `step_outputs`:
```python
            outputs['e3'] = {
                'project_name': result.get('project_name', ''),
                'section_count': result.get('section_count', 0),
                'output_file': result.get('output_file', ''),
            }
```

Replace it with:
```python
            outputs['e3'] = {
                'project_name': result.get('project_name', ''),
                'section_count': result.get('section_count', 0),
                'output_file': result.get('output_file', ''),
                'pdf_file': result.get('pdf_file') or '',
            }
```

No other changes to `e3_routes.py`.

---

## Step 5 — Update `backend/app/routers/rfp.py`

Make two targeted changes — one in `_collect_outputs` and one in
`_resolve_output_path`. Do not modify any other function.

### 5A. `_collect_outputs`

Find the loop that builds the file list. It ends with the `e5` entry:
```python
    for key, engine, label, canonical_name in [
        ("e2", "E2", "BoM Workbook", "bom_workbook.xlsx"),
        ("e3", "E3", "Technical Proposal", "technical_proposal.docx"),
        ("e4", "E4", "RFI Questionnaire", "rfi_questionnaire.xlsx"),
        ("e5", "E5", "Design Document", "design_document.docx"),
    ]:
        output_file = (outputs.get(key) or {}).get("output_file")
        if output_file:
            add_file(engine, label, canonical_name, output_dirs[key] / Path(output_file).name)
```

Add these lines immediately after the loop (after the `add_file` call):
```python
    # Submission PDF (generated alongside the E3 DOCX)
    e3_pdf = (outputs.get("e3") or {}).get("pdf_file")
    if e3_pdf:
        add_file("E3", "Submission PDF", "submission.pdf", output_dirs["e3"] / Path(e3_pdf).name)
```

### 5B. `_resolve_output_path`

Find the `candidates` dict that maps logical filenames to real paths. It ends with
the e5 block:
```python
    for key, canonical_name in [
        ("e2", "bom_workbook.xlsx"),
        ("e3", "technical_proposal.docx"),
        ("e4", "rfi_questionnaire.xlsx"),
        ("e5", "design_document.docx"),
    ]:
        output_file = (outputs.get(key) or {}).get("output_file")
        if output_file:
            actual_name = Path(output_file).name
            path = output_dirs[key] / actual_name
            candidates[canonical_name] = path
            candidates[actual_name] = path
```

Add these lines immediately after the loop:
```python
    # Submission PDF
    e3_pdf = (outputs.get("e3") or {}).get("pdf_file")
    if e3_pdf:
        actual_name = Path(e3_pdf).name
        path = output_dirs["e3"] / actual_name
        candidates["submission.pdf"] = path
        candidates[actual_name] = path
```

---

## Step 6 — Validation steps

Run each check in order. Fix any failure before the next.

### 6A. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e3/step7_pdf_converter.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e3/pipeline.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e3_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/routers/rfp.py
```
Expected: no output from any command.

### 6B. Import check
```
backend\.venv\Scripts\python.exe -c "
from app.engines.e3.step7_pdf_converter import convert_docx_to_pdf, _find_soffice
from app.engines.e3.pipeline import run_e3_pipeline
print('imports OK')
soffice = _find_soffice()
print(f'LibreOffice found: {soffice}')
"
```
Expected: `imports OK` then either a path to soffice or `LibreOffice found: None`.

### 6C. Unit test the converter with a real DOCX

There should be at least one DOCX in `backend/app/engines/e3/output/`. Run:

```
backend\.venv\Scripts\python.exe -c "
from pathlib import Path
from app.engines.e3.step7_pdf_converter import convert_docx_to_pdf

output_dir = Path('backend/app/engines/e3/output')
docx_files = list(output_dir.glob('*.docx'))

if not docx_files:
    print('SKIP: no DOCX files in output directory to test with')
else:
    docx = docx_files[0]
    print(f'Testing conversion of: {docx.name}')
    result = convert_docx_to_pdf(docx, output_dir)
    if result is None:
        print('RESULT: PDF conversion returned None (LibreOffice unavailable or failed)')
    elif result.exists():
        print(f'RESULT: PDF created at {result.name} ({result.stat().st_size} bytes)')
    else:
        print('RESULT: converter returned a path but file does not exist')
"
```
Expected: either `PDF created at *.pdf (N bytes)` or a clear `None` message.
Both are acceptable — the converter must not raise an exception.

### 6D. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 6E. Frontend build
```
cd frontend && npm run build
```
Expected: zero errors.

### 6F. API integration test

Start the backend. Use an opportunity ID that has completed E3 (`status = e3_complete`).
Substitute `<API_KEY>` and `<OPP_ID>`.

**List outputs — submission.pdf should appear if conversion succeeded:**
```
curl -s -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs | python -m json.tool
```
Expected: if LibreOffice is available, `submission.pdf` appears in the `outputs` array
with `"engine": "E3"`. If LibreOffice was unavailable during E3 generation, it will
not appear (acceptable).

**Download submission.pdf:**
```
curl -s -I -H "X-API-Key: <API_KEY>" \
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs/submission.pdf
```
Expected: HTTP 200 with `Content-Type: application/pdf` and
`Content-Disposition: attachment; filename="submission.pdf"`.
If the PDF was not generated: HTTP 404 (acceptable — converter was unavailable).

**Re-generate E3 to trigger PDF conversion with new code:**

If the existing E3 opportunities were generated before this change, run E3 again:
```
curl -s -X POST http://localhost:8000/api/e3/generate \
  -H "X-API-Key: <API_KEY>" \
  -F "rfp_session_id=<OPP_ID>" \
  -F "gbb_tier=better" | python -m json.tool
```
Expected response includes `"pdf_file": "<filename>.pdf"` (or `null` if LibreOffice
unavailable).

---

## Step 7 — Summary of files changed

| Action   | File path                                            |
|----------|------------------------------------------------------|
| Created  | `backend/app/engines/e3/step7_pdf_converter.py`      |
| Modified | `backend/app/engines/e3/pipeline.py`                 |
| Modified | `backend/app/api/e3_routes.py`                       |
| Modified | `backend/app/routers/rfp.py`                         |

No frontend changes needed — the `DownloadButton` for `submission.pdf` already exists
in `frontend/app/e3/[id]/review/page.tsx` and calls the generic download endpoint.
No DB migration needed.

---

## Step 8 — Git commit message

```
feat: add E3 PDF generation via LibreOffice headless conversion

- backend/app/engines/e3/step7_pdf_converter.py: convert_docx_to_pdf()
  Finds LibreOffice across Windows/Linux/macOS paths, runs headless
  --convert-to pdf subprocess, returns PDF Path or None on any failure.
  Never raises — all exceptions are caught and logged.

- engines/e3/pipeline.py: call convert_docx_to_pdf after write_proposal;
  add pdf_file key to pipeline result (None if conversion unavailable)

- api/e3_routes.py: persist pdf_file into step_outputs["e3"]["pdf_file"]

- routers/rfp.py: extend _collect_outputs and _resolve_output_path to
  map "submission.pdf" logical name to the stored pdf_file path.
  The existing DownloadButton in the E3 review page now resolves correctly.

Conversion is best-effort: DOCX download is unaffected if LibreOffice
is not installed.
```
