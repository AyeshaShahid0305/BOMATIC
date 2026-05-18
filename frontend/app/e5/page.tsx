"use client";
import { useState } from "react";

type E5Result = {
  output_file: string;
  project_name: string;
  hld_section_count: number;
  lld_section_count: number;
  generated_from: string;
  total_sections: number;
};

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

export default function E5Page() {
  const [sessionId, setSessionId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<E5Result | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    if (!sessionId.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("rfp_session_id", sessionId.trim());

    try {
      const res = await fetch("/api/e5/generate", { method: "POST", body: form });
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

  const canSubmit = sessionId.trim().length > 0 && !loading;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">

        {/* Page header */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-100 text-sm font-bold text-indigo-700">
            E5
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">HLD/LLD Generator</h1>
            <p className="text-sm text-gray-500">
              Generate a professional High Level Design and Low Level Design document from your RFP session
            </p>
          </div>
        </div>

        {/* ── Section 1: Inputs ── */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-6 py-4">
            <h2 className="text-base font-semibold text-gray-800">1 — Inputs</h2>
          </div>

          <div className="space-y-5 px-6 py-5">
            <div className="space-y-1.5">
              <label htmlFor="session-id" className="text-sm font-medium text-gray-700">
                RFP Session ID
              </label>
              <input
                id="session-id"
                type="text"
                value={sessionId}
                onChange={e => setSessionId(e.target.value)}
                placeholder="e.g. OPP-A1B2C3D4"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <p className="text-xs text-gray-400">
                The opportunity ID from your completed E1 analysis
              </p>
            </div>

            {error && !result && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={!canSubmit}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading && <Spinner />}
              {loading ? "Generating…" : "Generate HLD/LLD"}
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
              {/* Project name */}
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Project</p>
                <p className="mt-0.5 text-base font-semibold text-gray-900">{result.project_name}</p>
              </div>

              {/* Stat cards */}
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-center">
                  <p className="text-2xl font-bold text-indigo-700">{result.total_sections}</p>
                  <p className="mt-0.5 text-xs text-gray-500">Total Sections</p>
                </div>
                <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-center">
                  <p className="text-2xl font-bold text-indigo-700">{result.hld_section_count}</p>
                  <p className="mt-0.5 text-xs text-gray-500">HLD Sections</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-center">
                  <p className="text-2xl font-bold text-gray-900">{result.lld_section_count}</p>
                  <p className="mt-0.5 text-xs text-gray-500">LLD Sections</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-center">
                  <p className="text-sm font-bold text-gray-900 capitalize">
                    {result.generated_from === "e1" ? "E1 Session" : "Blank"}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500">Generated From</p>
                </div>
              </div>

              {/* Download button */}
              <a
                href={`/api/e5/download/${encodeURIComponent(result.output_file)}`}
                className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 4v11" />
                </svg>
                Download HLD/LLD Document
              </a>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
