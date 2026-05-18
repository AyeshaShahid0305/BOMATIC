"use client";
import { useRef, useState } from "react";

type E2Result = {
  output_file: string;
  matched_count: number;
  unmatched_count: number;
  low_confidence_count: number;
  subtotal: number;
  discount_amount: number;
  total: number;
  currency: string;
};

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

function fmt(n: number) {
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function E2Page() {
  const [sessionId, setSessionId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<E2Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">

        {/* Page header */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-100 text-sm font-bold text-green-700">
            E2
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">BoM Builder</h1>
            <p className="text-sm text-gray-500">
              Generate a priced Bill of Materials from your RFP session and BoQ template
            </p>
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
              <label htmlFor="session-id" className="text-sm font-medium text-gray-700">
                RFP Session ID
              </label>
              <input
                id="session-id"
                type="text"
                value={sessionId}
                onChange={e => setSessionId(e.target.value)}
                placeholder="e.g. OP-2024-001"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-400">
                The opportunity ID from your completed E1 analysis
              </p>
            </div>

            {/* BoQ template upload */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">
                BoQ Template (.xlsx / .xls)
              </label>
              <div
                onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) pickFile(f); }}
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onClick={() => inputRef.current?.click()}
                className={`cursor-pointer rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors ${
                  dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-gray-50 hover:border-gray-400"
                }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) pickFile(f); e.target.value = ""; }}
                />
                {file ? (
                  <div className="flex items-center justify-center gap-2 text-sm text-gray-700">
                    <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 4H7a2 2 0 01-2-2V6a2 2 0 012-2h7l5 5v11a2 2 0 01-2 2z" />
                    </svg>
                    <span className="font-medium">{file.name}</span>
                    <span className="text-gray-400">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                ) : (
                  <>
                    <p className="text-sm text-gray-500">
                      Drag & drop your BoQ template, or{" "}
                      <span className="text-blue-600 underline">browse</span>
                    </p>
                    <p className="mt-1 text-xs text-gray-400">.xlsx and .xls only</p>
                  </>
                )}
              </div>
              {file && (
                <button
                  onClick={() => setFile(null)}
                  className="text-xs text-gray-400 hover:text-red-500"
                >
                  ✕ Remove file
                </button>
              )}
            </div>

            {/* Inline error (input validation or API error before result) */}
            {error && !result && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={!canSubmit}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading && <Spinner />}
              {loading ? "Generating…" : "Generate BoQ"}
            </button>
          </div>
        </div>

        {/* ── Section 2: Results ── */}
        {result && (
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-100 px-6 py-4">
              <h2 className="text-base font-semibold text-gray-800">2 — Results</h2>
            </div>

            <div className="space-y-5 px-6 py-5">
              {/* Warning banner */}
              {result.unmatched_count > 0 && (
                <div className="flex items-start gap-3 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                  </svg>
                  <p className="text-sm text-yellow-800">
                    <span className="font-semibold">
                      {result.unmatched_count} item{result.unmatched_count !== 1 ? "s" : ""}
                    </span>{" "}
                    need manual review in the downloaded file. Look for{" "}
                    <span className="font-medium">NEEDS REVIEW</span> rows highlighted in red.
                  </p>
                </div>
              )}

              {/* Count cards */}
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-center">
                  <p className="text-2xl font-bold text-gray-900">{result.matched_count}</p>
                  <p className="mt-0.5 text-xs text-gray-500">Matched</p>
                </div>
                <div className={`rounded-lg border px-4 py-3 text-center ${
                  result.unmatched_count > 0
                    ? "border-yellow-200 bg-yellow-50"
                    : "border-gray-200 bg-gray-50"
                }`}>
                  <p className={`text-2xl font-bold ${result.unmatched_count > 0 ? "text-yellow-700" : "text-gray-900"}`}>
                    {result.unmatched_count}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500">Unmatched</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-center">
                  <p className="text-2xl font-bold text-gray-900">{result.low_confidence_count}</p>
                  <p className="mt-0.5 text-xs text-gray-500">Low Confidence</p>
                </div>
              </div>

              {/* Pricing summary */}
              <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
                <div className="flex items-center justify-between px-4 py-3">
                  <span className="text-sm text-gray-600">Subtotal</span>
                  <span className="text-sm font-medium text-gray-900">
                    {result.currency} {fmt(result.subtotal)}
                  </span>
                </div>
                <div className="flex items-center justify-between px-4 py-3">
                  <span className="text-sm text-gray-600">Discount (15% SI)</span>
                  <span className="text-sm font-medium text-green-700">
                    − {result.currency} {fmt(result.discount_amount)}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-b-lg bg-gray-50 px-4 py-3">
                  <span className="text-sm font-semibold text-gray-800">Total</span>
                  <span className="text-base font-bold text-gray-900">
                    {result.currency} {fmt(result.total)}
                  </span>
                </div>
              </div>

              {/* Download button */}
              <a
                href={`/api/e2/download/${encodeURIComponent(result.output_file)}`}
                className="flex items-center justify-center gap-2 rounded-lg bg-green-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-green-700"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 4v11" />
                </svg>
                Download Excel BoQ
              </a>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
