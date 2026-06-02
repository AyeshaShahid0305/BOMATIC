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
          <h1 className="mt-2 text-2xl font-bold text-gray-900">E2  Bill of Materials Review</h1>
          <p className="mt-1 text-sm text-gray-500">Opportunity {id}</p>
        </div>

        {loading && <p className="text-sm text-gray-400">Loading</p>}
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
                 E2 approved. <a href={`/e3?session_id=${encodeURIComponent(id)}`} className="underline font-semibold">Generate the Technical Proposal </a>
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
               Opportunities
            </a>
            <button
              onClick={handleApprove}
              disabled={approving || approved}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {approving && <Spinner />}
              {approved ? "Approved" : approving ? "Approving" : "Approve & Continue to E3"}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
