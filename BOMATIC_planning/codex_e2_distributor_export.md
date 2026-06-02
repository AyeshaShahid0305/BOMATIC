# Codex Task: E2 Distributor Export

## Context

BOMATIC is a FastAPI + Next.js + PostgreSQL pre-sales platform. E2 currently
produces one Excel file: a filled BoM workbook (`bom_workbook.xlsx`) that contains
BOMATIC-internal columns (Match Method, Match Score, Discount %). Distributors
need a clean, stripped-down version with only the columns they require to process
a purchase order.

The E2 review page (`frontend/app/e2/[id]/page.tsx`) already renders a
`DownloadButton` for `distributor_export.xlsx` — it 404s because the file is
never created.

This task adds a second Excel writer function that produces the distributor export
alongside the existing BoM workbook. No frontend changes are needed.

**Distributor export format:**
- Sheet name: `Distributor Order`
- Columns (in order): SKU, Description, Quantity, Unit Price (USD), Total Price (USD)
- Rows: matched items only — no unmatched/NEEDS REVIEW rows
- Final row: totals (blank SKU, "TOTAL" in Description, sum of Qty, blank Unit Price,
  sum of Total Price)
- Bold header row, bold totals row, no other formatting required
- Filename: `{template_stem}_Distributor_Export.xlsx` (new workbook, not the filled template)

---

## Step 1 — Read these files first (in this order)

Read every file completely before writing any code.

1. `backend/app/engines/e2/step5_excel_writer.py`
2. `backend/app/engines/e2/pipeline.py`
3. `backend/app/engines/e2/models.py`
4. `backend/app/api/e2_routes.py`
5. `backend/app/routers/rfp.py`

---

## Step 2 — Update `backend/app/engines/e2/step5_excel_writer.py`

Add one new function at the bottom of the file, after the existing `write_output`
function and `_first_empty_row` helper. Do not modify any existing function.

```python
def write_distributor_export(
    summary: PricingSummary,
    template_path: Path,
) -> Path:
    """
    Write a clean distributor-facing Excel file containing only matched items.

    Columns: SKU | Description | Quantity | Unit Price (USD) | Total Price (USD)
    Includes a bold totals row. Unmatched items are excluded.
    Returns the path to the generated file.
    """
    _OUTPUT_DIR.mkdir(exist_ok=True)

    stem = Path(template_path).stem
    output_path = _OUTPUT_DIR / f"{stem}_Distributor_Export.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Distributor Order"

    # Header row
    headers = ["SKU", "Description", "Quantity", "Unit Price (USD)", "Total Price (USD)"]
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=title)
        cell.font = _BOLD

    # Data rows — matched items only
    row = 2
    total_qty = 0.0
    total_price = 0.0

    for m in summary.matched_items:
        qty = m.rfp_item.quantity if m.rfp_item.quantity is not None else 1.0
        line_total = round(qty * m.unit_price, 2)
        total_qty += qty
        total_price += line_total

        ws.cell(row=row, column=1, value=m.sku)
        ws.cell(row=row, column=2, value=m.rfp_item.description)
        ws.cell(row=row, column=3, value=qty)
        ws.cell(row=row, column=4, value=round(m.unit_price, 2))
        ws.cell(row=row, column=5, value=line_total)
        row += 1

    # Totals row
    totals_cells = [
        (row, 1, ""),
        (row, 2, "TOTAL"),
        (row, 3, total_qty),
        (row, 4, ""),
        (row, 5, round(total_price, 2)),
    ]
    for r, c, v in totals_cells:
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = _BOLD

    # Auto-fit column widths (best-effort)
    col_widths = [16, 45, 10, 18, 18]
    for col, width in enumerate(col_widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width

    wb.save(output_path)
    return output_path
```

---

## Step 3 — Update `backend/app/engines/e2/pipeline.py`

Make two targeted changes only.

**Change 1 — Add import.**

Find the existing imports block:
```python
from .step5_excel_writer import write_output
```

Replace with:
```python
from .step5_excel_writer import write_output, write_distributor_export
```

**Change 2 — Call `write_distributor_export` after `write_output` and add result.**

Find:
```python
    output_path = write_output(summary, template_path, detection)

    return {
        "output_file": output_path,
```

Replace with:
```python
    output_path = write_output(summary, template_path, detection)
    distributor_path = write_distributor_export(summary, template_path)

    return {
        "output_file": output_path,
        "distributor_file": distributor_path.name,
```

No other changes to `pipeline.py`.

---

## Step 4 — Update `backend/app/api/e2_routes.py`

Make one targeted change only. Find the block that writes to `step_outputs`:

```python
            outputs['e2'] = {
                'matched_items': result.get('matched_items', []),
                'subtotal': result.get('subtotal', 0),
                'total_price': result.get('total_price', 0),
                'vendor_list': result.get('vendor_list', []),
                'requirements_baseline_count': result.get('requirements_baseline_count', 0),
                'output_file': Path(result['output_file']).name,
            }
```

Replace with:
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

No other changes to `e2_routes.py`.

---

## Step 5 — Update `backend/app/routers/rfp.py`

Make two targeted changes — one in `_collect_outputs` and one in
`_resolve_output_path`. Do not modify any other function.

### 5A. `_collect_outputs`

Find the block added for the E3 PDF that reads:
```python
    # Submission PDF (generated alongside the E3 DOCX)
    e3_pdf = (outputs.get("e3") or {}).get("pdf_file")
    if e3_pdf:
        add_file("E3", "Submission PDF", "submission.pdf", output_dirs["e3"] / Path(e3_pdf).name)
```

Add the distributor export block immediately before it:
```python
    # E2 Distributor Export
    e2_distributor = (outputs.get("e2") or {}).get("distributor_file")
    if e2_distributor:
        add_file("E2", "Distributor Export", "distributor_export.xlsx", output_dirs["e2"] / Path(e2_distributor).name)

    # Submission PDF (generated alongside the E3 DOCX)
```

### 5B. `_resolve_output_path`

Find the block added for the E3 PDF that reads:
```python
    # Submission PDF
    e3_pdf = (outputs.get("e3") or {}).get("pdf_file")
    if e3_pdf:
        actual_name = Path(e3_pdf).name
        path = output_dirs["e3"] / actual_name
        candidates["submission.pdf"] = path
        candidates[actual_name] = path
```

Add the distributor export block immediately before it:
```python
    # E2 Distributor Export
    e2_distributor = (outputs.get("e2") or {}).get("distributor_file")
    if e2_distributor:
        actual_name = Path(e2_distributor).name
        path = output_dirs["e2"] / actual_name
        candidates["distributor_export.xlsx"] = path
        candidates[actual_name] = path

    # Submission PDF
```

---

## Step 6 — Validation steps

Run each check in order. Fix any failure before the next.

### 6A. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e2/step5_excel_writer.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e2/pipeline.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e2_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/routers/rfp.py
```
Expected: no output from any command.

### 6B. Import check
```
backend\.venv\Scripts\python.exe -c "
from app.engines.e2.step5_excel_writer import write_output, write_distributor_export
from app.engines.e2.pipeline import run_e2_pipeline
print('imports OK')
"
```
Expected: `imports OK`

### 6C. Unit test the distributor export writer with mock data
```
backend\.venv\Scripts\python.exe -c "
import tempfile
from pathlib import Path
from app.engines.e2.models import CatalogMatch, PricingSummary, RFPLineItem
from app.engines.e2.step5_excel_writer import write_distributor_export

summary = PricingSummary(
    matched_items=[
        CatalogMatch(
            rfp_item=RFPLineItem('Cisco ASA 5516-X', 2.0, 'units', 'security', '', 0.9),
            sku='ASA5516-FPWR-K9', product_name='Cisco ASA 5516-X', vendor='Cisco',
            unit_price=4995.0, match_score=1.0, match_method='exact',
        ),
        CatalogMatch(
            rfp_item=RFPLineItem('48-port PoE+ switch', 10.0, 'units', 'network', '', 0.85),
            sku='C9300-48P-E', product_name='Catalyst 9300', vendor='Cisco',
            unit_price=7200.0, match_score=0.9, match_method='exact',
        ),
    ],
    unmatched_items=[],
    low_confidence_items=[],
    subtotal=81990.0,
    discount_amount=12298.5,
    total=69691.5,
    currency='USD',
)

# Use a dummy template path for the filename stem
dummy = Path('test_template.xlsx')
out = write_distributor_export(summary, dummy)
print(f'Created: {out.name}')

import openpyxl
wb = openpyxl.load_workbook(out)
ws = wb.active
assert ws.title == 'Distributor Order', f'Wrong sheet name: {ws.title}'
assert ws.cell(1, 1).value == 'SKU', 'Missing SKU header'
# 2 data rows + 1 totals = row 4 should be totals
totals_row = ws.max_row
assert ws.cell(totals_row, 2).value == 'TOTAL', f'Missing TOTAL row, got: {ws.cell(totals_row, 2).value}'
assert ws.cell(totals_row, 5).value == round(2*4995 + 10*7200, 2), 'Wrong total price'
print('All assertions passed.')
out.unlink()  # clean up test file
"
```
Expected: `Created: test_template_Distributor_Export.xlsx` then `All assertions passed.`

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

Start the backend. Run E2 on an opportunity that has E1 complete, then check outputs.
Substitute `<API_KEY>` and `<OPP_ID>`.

**Run E2:**
```
curl -s -X POST http://localhost:8000/api/e2/analyze ^
  -H "X-API-Key: <API_KEY>" ^
  -F "rfp_session_id=<OPP_ID>" ^
  -F "boq_template=@path\to\a\boq.xlsx" | python -m json.tool
```
Expected response includes `"distributor_file": "<stem>_Distributor_Export.xlsx"`.

**List outputs — distributor_export.xlsx should appear:**
```
curl -s -H "X-API-Key: <API_KEY>" ^
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs | python -m json.tool
```
Expected: `distributor_export.xlsx` in the outputs array with `"engine": "E2"`.

**Download distributor export:**
```
curl -s -I -H "X-API-Key: <API_KEY>" ^
  http://localhost:8000/api/v1/rfp/packages/<OPP_ID>/outputs/distributor_export.xlsx
```
Expected: HTTP 200 with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

---

## Step 7 — Summary of files changed

| Action   | File path                                          |
|----------|----------------------------------------------------|
| Modified | `backend/app/engines/e2/step5_excel_writer.py`     |
| Modified | `backend/app/engines/e2/pipeline.py`               |
| Modified | `backend/app/api/e2_routes.py`                     |
| Modified | `backend/app/routers/rfp.py`                       |

No frontend changes. No DB migration. No new files created.

---

## Step 8 — Git commit message

```
feat: add E2 distributor export as a separate generated file

- step5_excel_writer.py: write_distributor_export(summary, template_path)
  Produces a clean workbook with columns SKU, Description, Quantity,
  Unit Price (USD), Total Price (USD). Matched items only. Bold totals row.
  Named {template_stem}_Distributor_Export.xlsx in the e2 output directory.

- pipeline.py: call write_distributor_export after write_output; add
  distributor_file key to pipeline result dict

- e2_routes.py: persist distributor_file into step_outputs["e2"]["distributor_file"]

- rfp.py: extend _collect_outputs and _resolve_output_path to map
  "distributor_export.xlsx" to the stored distributor_file path.
  The existing DownloadButton in the E2 review page now resolves correctly.
```
