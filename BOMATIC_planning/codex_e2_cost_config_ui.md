# Codex Task: E2 Cost Stack Config UI

## Context

BOMATIC's E2 cost stack currently uses hardcoded defaults from
`cost_stack_defaults.json` — every opportunity gets SAR currency, 30% vendor
discount, 25% margin, and Saudi VAT regardless of the actual deal. Engineers
need to set these before generating the BoM.

This task adds a Pricing Config section to the E2 generator page, wires those
values through the API to the pipeline, and updates the results display to show
the full cost stack breakdown (sell price, VAT, total with VAT in the selected
currency).

**Fields to expose:**
- Target Currency (select: USD/SAR/AED/EGP/KWD/QAR/BHD/OMR/GBP/EUR)
- VAT Country (select: determines VAT rate — SA/AE/EG/KW/QA/BH/OM/GB/DE/US)
- Vendor Discount % (number, 0–60, default 30)
- Inhouse Margin % (number, 0–30, default 10)
- Selling Mode (radio: Margin / Markup)
- Selling % (number, 0–50, default 25)

These are passed as plain `Form(...)` fields alongside the existing file upload —
no JSON encoding needed.

---

## Step 1 — Read these files first

1. `frontend/app/e2/page.tsx` — full file
2. `backend/app/api/e2_routes.py` — analyze_boq function signature
3. `backend/app/engines/e2/pipeline.py`
4. `backend/app/engines/e2/step6_cost_stack.py` — load_defaults()
5. `backend/app/engines/e2/data/cost_stack_defaults.json`

---

## Step 2 — Update `backend/app/engines/e2/pipeline.py`

**Add import:**
```python
from .step6_cost_stack import run_cost_stack, load_defaults
```
(This import already exists — do not add a duplicate.)

**Update `run_e2_pipeline` signature** to accept optional `cost_config`:

Find:
```python
def run_e2_pipeline(
    rfp_text: str,
    template_path: Path,
    e1_output: E1Output | None = None,
) -> dict:
```

Replace with:
```python
def run_e2_pipeline(
    rfp_text: str,
    template_path: Path,
    e1_output: E1Output | None = None,
    cost_config: dict | None = None,
) -> dict:
```

**Use `cost_config` when calling `run_cost_stack`**. Find:
```python
    cost_config = load_defaults()
    cost_stack_result = run_cost_stack(summary, cost_config)
```

Replace with:
```python
    effective_config = cost_config if cost_config is not None else load_defaults()
    cost_stack_result = run_cost_stack(summary, effective_config)
```

No other changes to `pipeline.py`.

---

## Step 3 — Update `backend/app/api/e2_routes.py`

**Add cost config form fields to `analyze_boq`.**

Find the function signature:
```python
async def analyze_boq(
    rfp_session_id: str = Form(default=""),
    boq_template: UploadFile = File(...),
    db: Session = Depends(get_db),
):
```

Replace with:
```python
async def analyze_boq(
    rfp_session_id: str = Form(default=""),
    boq_template: UploadFile = File(...),
    target_currency: str = Form(default="SAR"),
    vat_country: str = Form(default="SA"),
    vendor_discount_pct: float = Form(default=0.30),
    inhouse_margin_pct: float = Form(default=0.10),
    selling_mode: str = Form(default="margin"),
    selling_pct: float = Form(default=0.25),
    db: Session = Depends(get_db),
):
```

**Build cost_config dict and pass to pipeline.** Find the line that calls
`run_e2_pipeline`:
```python
        result = run_e2_pipeline(rfp_text, template_path, e1_output=e1_output)
```

Replace with:
```python
        from app.engines.e2.step6_cost_stack import load_defaults
        cost_config = load_defaults()
        cost_config["target_currency"] = target_currency
        cost_config["vat_country"] = vat_country
        cost_config["vendor_discount_pct"] = max(0.0, min(0.99, vendor_discount_pct))
        cost_config["inhouse_margin_pct"] = max(0.0, min(0.99, inhouse_margin_pct))
        cost_config["selling_mode"] = selling_mode if selling_mode in ("margin", "markup") else "margin"
        cost_config["selling_pct"] = max(0.0, min(0.99, selling_pct))
        result = run_e2_pipeline(rfp_text, template_path, e1_output=e1_output,
                                  cost_config=cost_config)
```

**Add `cost_config_used` to step_outputs["e2"]** (alongside the existing fields):
```python
                'cost_config': {
                    'target_currency': target_currency,
                    'vat_country': vat_country,
                    'vendor_discount_pct': vendor_discount_pct,
                    'inhouse_margin_pct': inhouse_margin_pct,
                    'selling_mode': selling_mode,
                    'selling_pct': selling_pct,
                },
```

No other changes to `e2_routes.py`.

---

## Step 4 — Replace `frontend/app/e2/page.tsx`

Replace the entire file with this content:

```tsx
"use client";
import { useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type CostConfig = {
  target_currency: string;
  vat_country: string;
  vendor_discount_pct: number;
  inhouse_margin_pct: number;
  selling_mode: "margin" | "markup";
  selling_pct: number;
};

type CostStackSummary = {
  total_list_local: number;
  total_cost: number;
  total_sell: number;
  cs008_stcs_sale_total: number;
  total_vat: number;
  total_with_vat: number;
  currency: string;
  fx_rate: number;
  vat_rate: number;
  vat_country: string;
  line_count: number;
};

type E2Result = {
  output_file: string;
  matched_count: number;
  unmatched_count: number;
  low_confidence_count: number;
  subtotal: number;
  discount_amount: number;
  total: number;
  currency: string;
  cost_stack?: CostStackSummary;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CURRENCIES = [
  { code: "SAR", label: "SAR — Saudi Riyal" },
  { code: "AED", label: "AED — UAE Dirham" },
  { code: "USD", label: "USD — US Dollar" },
  { code: "EGP", label: "EGP — Egyptian Pound" },
  { code: "KWD", label: "KWD — Kuwaiti Dinar" },
  { code: "QAR", label: "QAR — Qatari Riyal" },
  { code: "BHD", label: "BHD — Bahraini Dinar" },
  { code: "OMR", label: "OMR — Omani Rial" },
  { code: "GBP", label: "GBP — British Pound" },
  { code: "EUR", label: "EUR — Euro" },
];

const VAT_COUNTRIES = [
  { code: "SA", label: "Saudi Arabia (15%)" },
  { code: "AE", label: "UAE (5%)" },
  { code: "EG", label: "Egypt (14%)" },
  { code: "BH", label: "Bahrain (10%)" },
  { code: "OM", label: "Oman (5%)" },
  { code: "KW", label: "Kuwait (0%)" },
  { code: "QA", label: "Qatar (0%)" },
  { code: "GB", label: "United Kingdom (20%)" },
  { code: "DE", label: "Germany (19%)" },
  { code: "US", label: "USA (0%)" },
];

const DEFAULT_CONFIG: CostConfig = {
  target_currency: "SAR",
  vat_country: "SA",
  vendor_discount_pct: 30,
  inhouse_margin_pct: 10,
  selling_mode: "margin",
  selling_pct: 25,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number, currency?: string) {
  const prefix = currency ? `${currency} ` : "";
  return prefix + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-gray-700">{children}</label>;
}

function NumInput({
  value, onChange, min = 0, max = 99, step = 1, suffix
}: {
  value: number; onChange: (v: number) => void;
  min?: number; max?: number; step?: number; suffix?: string;
}) {
  return (
    <div className="flex items-center gap-1">
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-24 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      {suffix && <span className="text-sm text-gray-500">{suffix}</span>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function E2Page() {
  const [sessionId, setSessionId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<E2Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<CostConfig>(DEFAULT_CONFIG);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("session_id") ?? params.get("rfp_session_id");
    if (id) setSessionId(id);
  }, []);

  function setField<K extends keyof CostConfig>(key: K, value: CostConfig[K]) {
    setConfig(prev => ({ ...prev, [key]: value }));
  }

  function pickFile(f: File) {
    if (!f.name.match(/\.(xlsx|xls)$/i)) {
      setError("Only .xlsx and .xls files are accepted.");
      return;
    }
    setError(null);
    setFile(f);
  }

  async function handleGenerate() {
    if (!sessionId.trim() || !file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("rfp_session_id", sessionId.trim());
    form.append("boq_template", file);
    form.append("target_currency", config.target_currency);
    form.append("vat_country", config.vat_country);
    form.append("vendor_discount_pct", String(config.vendor_discount_pct / 100));
    form.append("inhouse_margin_pct", String(config.inhouse_margin_pct / 100));
    form.append("selling_mode", config.selling_mode);
    form.append("selling_pct", String(config.selling_pct / 100));

    try {
      const res = await fetch("/api/e2/analyze", { method: "POST", body: form });
      if (!res.ok) {
        let detail = `Server error ${res.status}`;
        try { detail = (await res.json()).detail ?? detail; } catch { /* use default */ }
        throw new Error(detail);
      }
      setResult(await res.json());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = sessionId.trim().length > 0 && file !== null && !loading;
  const cs = result?.cost_stack;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-100 text-sm font-bold text-green-700">E2</div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">BoM Builder</h1>
            <p className="text-sm text-gray-500">Generate a priced Bill of Materials from your RFP session and BoQ template</p>
          </div>
        </div>

        {/* ── Section 1: Inputs ── */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-6 py-4">
            <h2 className="text-base font-semibold text-gray-800">1 — Inputs</h2>
          </div>
          <div className="space-y-5 px-6 py-5">

            {/* Session ID */}
            <div className="space-y-1.5">
              <FieldLabel>RFP Session ID</FieldLabel>
              <input
                type="text"
                value={sessionId}
                onChange={e => setSessionId(e.target.value)}
                placeholder="e.g. OPP-2024-001"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-400">The opportunity ID from your completed E1 analysis</p>
            </div>

            {/* BoQ file upload */}
            <div className="space-y-1.5">
              <FieldLabel>BoQ Template (.xlsx / .xls)</FieldLabel>
              <div
                onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) pickFile(f); }}
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onClick={() => inputRef.current?.click()}
                className={`cursor-pointer rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors ${
                  dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-gray-50 hover:border-gray-400"
                }`}
              >
                <input ref={inputRef} type="file" accept=".xlsx,.xls" className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) pickFile(f); e.target.value = ""; }} />
                {file ? (
                  <div className="flex items-center justify-center gap-2 text-sm text-gray-700">
                    <span className="font-medium">{file.name}</span>
                    <span className="text-gray-400">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                ) : (
                  <>
                    <p className="text-sm text-gray-500">Drag & drop your BoQ template, or <span className="text-blue-600 underline">browse</span></p>
                    <p className="mt-1 text-xs text-gray-400">.xlsx and .xls only</p>
                  </>
                )}
              </div>
              {file && (
                <button onClick={() => setFile(null)} className="text-xs text-gray-400 hover:text-red-500">&times; Remove file</button>
              )}
            </div>
          </div>
        </div>

        {/* ── Section 2: Pricing Config ── */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-6 py-4">
            <h2 className="text-base font-semibold text-gray-800">2 — Pricing Configuration</h2>
            <p className="mt-0.5 text-xs text-gray-400">Affects the cost stack calculation in the generated Excel output</p>
          </div>
          <div className="space-y-5 px-6 py-5">

            {/* Currency + VAT row */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <FieldLabel>Target Currency</FieldLabel>
                <select
                  value={config.target_currency}
                  onChange={e => setField("target_currency", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-blue-500 focus:outline-none"
                >
                  {CURRENCIES.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <FieldLabel>VAT Country</FieldLabel>
                <select
                  value={config.vat_country}
                  onChange={e => setField("vat_country", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-blue-500 focus:outline-none"
                >
                  {VAT_COUNTRIES.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}
                </select>
              </div>
            </div>

            {/* Discount + Margin row */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <FieldLabel>Vendor Discount</FieldLabel>
                <NumInput value={config.vendor_discount_pct} onChange={v => setField("vendor_discount_pct", v)} min={0} max={60} suffix="%" />
                <p className="text-xs text-gray-400">Trade discount off vendor list price</p>
              </div>
              <div className="space-y-1.5">
                <FieldLabel>Inhouse Margin</FieldLabel>
                <NumInput value={config.inhouse_margin_pct} onChange={v => setField("inhouse_margin_pct", v)} min={0} max={30} suffix="%" />
                <p className="text-xs text-gray-400">SI cost uplift before overhead</p>
              </div>
            </div>

            {/* Selling mode + percentage */}
            <div className="space-y-1.5">
              <FieldLabel>Selling Price Method</FieldLabel>
              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input type="radio" name="selling_mode" value="margin"
                    checked={config.selling_mode === "margin"}
                    onChange={() => setField("selling_mode", "margin")} />
                  Gross Margin (cost ÷ (1 − %))
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input type="radio" name="selling_mode" value="markup"
                    checked={config.selling_mode === "markup"}
                    onChange={() => setField("selling_mode", "markup")} />
                  Markup (cost × (1 + %))
                </label>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <NumInput value={config.selling_pct} onChange={v => setField("selling_pct", v)} min={1} max={50} suffix="%" />
                <span className="text-xs text-gray-400">
                  {config.selling_mode === "margin" ? "Gross margin target" : "Markup on cost"}
                </span>
              </div>
            </div>

            {/* Advanced toggle */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-blue-600 hover:text-blue-800 underline"
            >
              {showAdvanced ? "Hide advanced settings ▲" : "Show advanced settings ▼"}
            </button>

            {showAdvanced && (
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4 text-xs text-gray-500 space-y-1">
                <p className="font-medium text-gray-600">Fixed overhead components (10% total)</p>
                <p>Freight 2% · Customs 5% · Insurance 0.5% · Warehousing 1%</p>
                <p>Handling 0.5% · Finance 0.5% · Contingency 0.5%</p>
                <p className="mt-2 font-medium text-gray-600">STCS revenue share: 5%</p>
                <p>Embed discounts: none</p>
                <p className="mt-2 italic">To modify overhead, STCS share, or embed discounts, edit<br />
                  <code className="font-mono">backend/app/engines/e2/data/cost_stack_defaults.json</code>
                </p>
              </div>
            )}

          </div>
        </div>

        {/* Error + Generate */}
        {error && !result && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>
        )}

        <button
          onClick={handleGenerate}
          disabled={!canSubmit}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading && <Spinner />}
          {loading ? "Generating…" : "Generate BoM"}
        </button>

        {/* ── Section 3: Results ── */}
        {result && (
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-100 px-6 py-4">
              <h2 className="text-base font-semibold text-gray-800">3 — Results</h2>
            </div>
            <div className="space-y-5 px-6 py-5">

              {/* Unmatched warning */}
              {result.unmatched_count > 0 && (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
                  <span className="font-semibold">{result.unmatched_count} item(s)</span> need manual review.
                  Look for <span className="font-mono font-medium">NEEDS REVIEW</span> rows in the downloaded file.
                </div>
              )}

              {/* Match counts */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "Matched", value: result.matched_count, color: "text-gray-900" },
                  { label: "Unmatched", value: result.unmatched_count, color: result.unmatched_count > 0 ? "text-yellow-700" : "text-gray-900" },
                  { label: "Low Confidence", value: result.low_confidence_count, color: "text-gray-900" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-center">
                    <p className={`text-2xl font-bold ${color}`}>{value}</p>
                    <p className="mt-0.5 text-xs text-gray-500">{label}</p>
                  </div>
                ))}
              </div>

              {/* Cost stack summary */}
              {cs ? (
                <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
                  <div className="bg-gray-50 px-4 py-2.5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Cost Stack — {cs.currency} (FX: 1 USD = {cs.fx_rate} {cs.currency})
                    </p>
                  </div>
                  {[
                    ["List Price (local)", fmt(cs.total_list_local, cs.currency)],
                    ["Total Cost (with overhead)", fmt(cs.total_cost, cs.currency)],
                    ["Total Sell Price", fmt(cs.total_sell, cs.currency)],
                    [`VAT (${(cs.vat_rate * 100).toFixed(0)}% — ${cs.vat_country})`, fmt(cs.total_vat, cs.currency)],
                    ["Total incl. VAT", fmt(cs.total_with_vat, cs.currency)],
                    ["STCS Sale (after revenue share)", fmt(cs.cs008_stcs_sale_total, cs.currency)],
                  ].map(([label, value], i) => (
                    <div key={i} className={`flex items-center justify-between px-4 py-3 ${i === 3 || i === 4 ? "bg-blue-50" : ""}`}>
                      <span className="text-sm text-gray-600">{label}</span>
                      <span className={`text-sm font-semibold ${i === 4 ? "text-blue-800 text-base" : "text-gray-900"}`}>{value}</span>
                    </div>
                  ))}
                </div>
              ) : (
                // Fallback: show legacy subtotal/discount/total if no cost stack
                <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
                  <div className="flex justify-between px-4 py-3">
                    <span className="text-sm text-gray-600">Subtotal</span>
                    <span className="text-sm font-medium">{result.currency} {fmt(result.subtotal)}</span>
                  </div>
                  <div className="flex justify-between px-4 py-3">
                    <span className="text-sm text-gray-600">Discount (15% SI)</span>
                    <span className="text-sm font-medium text-green-700">− {result.currency} {fmt(result.discount_amount)}</span>
                  </div>
                  <div className="flex justify-between rounded-b-lg bg-gray-50 px-4 py-3">
                    <span className="text-sm font-semibold text-gray-800">Total</span>
                    <span className="text-base font-bold text-gray-900">{result.currency} {fmt(result.total)}</span>
                  </div>
                </div>
              )}

              {/* Download + next steps */}
              <a
                href={`/api/e2/download/${encodeURIComponent(result.output_file)}`}
                className="flex items-center justify-center gap-2 rounded-lg bg-green-600 px-6 py-3 text-sm font-medium text-white hover:bg-green-700"
              >
                Download BoM Workbook (Excel)
              </a>

              <div className="rounded-xl border border-green-200 bg-green-50 px-5 py-4">
                <h3 className="text-sm font-semibold text-green-900">Next Step</h3>
                <p className="mt-1 text-sm text-green-800">BoM generation complete. Continue with the same RFP session.</p>
                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <a href={`/e3?session_id=${encodeURIComponent(sessionId.trim())}`}
                    className="flex items-center justify-center rounded-lg bg-purple-600 px-4 py-3 text-sm font-semibold text-white hover:bg-purple-700">
                    Generate Technical Proposal
                  </a>
                  <a href="/opportunities"
                    className="flex items-center justify-center rounded-lg border border-green-200 bg-white px-4 py-3 text-sm font-semibold text-green-800 hover:bg-green-100">
                    Go to Opportunities
                  </a>
                </div>
              </div>

            </div>
          </div>
        )}

      </div>
    </div>
  );
}
```

---

## Step 5 — Validation steps

### 5A. Backend syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e2/pipeline.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e2_routes.py
```
Expected: no output.

### 5B. Import check
```
backend\.venv\Scripts\python.exe -c "
from app.engines.e2.pipeline import run_e2_pipeline
import inspect
sig = inspect.signature(run_e2_pipeline)
assert 'cost_config' in sig.parameters, 'cost_config param missing'
print('pipeline signature OK:', list(sig.parameters.keys()))
"
```
Expected: `pipeline signature OK: ['rfp_text', 'template_path', 'e1_output', 'cost_config']`

### 5C. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 5D. Frontend build
```
cd frontend && npm run build
```
Expected: zero errors.

### 5E. Route smoke test — config fields accepted
```
backend\.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, 'backend')
from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)
headers = {'X-API-Key': 'bomatic-dev-key'}

# Posting without a real BoQ — should get 422 (validation) not 500
# This confirms the new form fields are accepted by FastAPI
r = client.post('/api/e2/analyze',
    data={
        'rfp_session_id': '',
        'target_currency': 'AED',
        'vat_country': 'AE',
        'vendor_discount_pct': '0.35',
        'inhouse_margin_pct': '0.12',
        'selling_mode': 'markup',
        'selling_pct': '0.30',
    },
    files={'boq_template': ('test.xlsx', io.BytesIO(b'fake'), 'application/octet-stream')},
    headers=headers,
)
# 400/422 = validation error (expected — no real BoQ)
# 500 = broken (not expected)
assert r.status_code != 500, f'Got 500: {r.text}'
print(f'Form fields accepted (status {r.status_code}): PASS')
"
```
Expected: `Form fields accepted (status 4xx): PASS` (400 or 422, not 500).

---

## Step 6 — Summary of files changed

| Action   | File path                                |
|----------|------------------------------------------|
| Modified | `backend/app/engines/e2/pipeline.py`     |
| Modified | `backend/app/api/e2_routes.py`           |
| Modified | `frontend/app/e2/page.tsx`               |

No DB migration. No new dependencies.

---

## Step 7 — Git commit message

```
feat: add cost stack config UI to E2 BoM generator

frontend/app/e2/page.tsx:
- New "Pricing Configuration" section (Section 2) with:
  Target Currency select (10 currencies), VAT Country select (10 countries),
  Vendor Discount % input, Inhouse Margin % input, Selling Mode radio
  (margin/markup), Selling % input, Advanced settings toggle showing
  fixed overhead breakdown and instructions to edit defaults JSON
- Results section now shows full cost stack summary (list local, cost with
  overhead, sell price, VAT, total with VAT, STCS sale) when available;
  falls back to legacy subtotal/discount/total for old sessions
- Config values posted as form fields alongside file upload

backend/app/engines/e2/pipeline.py:
- run_e2_pipeline now accepts optional cost_config dict;
  uses load_defaults() as fallback when None

backend/app/api/e2_routes.py:
- analyze_boq accepts target_currency, vat_country, vendor_discount_pct,
  inhouse_margin_pct, selling_mode, selling_pct as Form fields;
  clamps values to valid ranges; builds config dict and passes to pipeline;
  stores cost_config in step_outputs["e2"]["cost_config"]
```
