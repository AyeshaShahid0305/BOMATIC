"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";

function Spinner() {
  return (
    <svg className="h-5 w-5 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className="h-20 w-20 text-green-500"
      strokeWidth={1.8}
      stroke="currentColor"
    >
      <circle cx="12" cy="12" r="11" className="fill-green-50 stroke-green-200" strokeWidth={1} />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 12.5l3.5 3.5 6-7" />
    </svg>
  );
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function CompletePage() {
  const { id } = useParams();
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/e1/${id}/state`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { setState(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/" className="hover:text-gray-800">BOMATIC</a>
            <span>/</span>
            <a href={`/e1/${id}`} className="hover:text-gray-800">Opportunity {id}</a>
            <span>/</span>
            <span className="font-medium text-gray-800">Complete</span>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-6 py-16">
        {/* Hero */}
        <div className="flex flex-col items-center text-center">
          <CheckIcon />
          <h1 className="mt-6 text-3xl font-bold text-gray-900">Compliance Matrix Complete</h1>
          <p className="mt-2 text-base text-gray-500">
            E1 RFP Parser pipeline finished successfully.
          </p>
        </div>

        {/* Summary row */}
        <div className="mt-10 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
            Pipeline Summary
          </h2>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Spinner />
              Loading details…
            </div>
          ) : (
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <dt className="text-xs font-medium text-gray-400 uppercase">Opportunity ID</dt>
                <dd className="mt-1 font-mono text-sm font-semibold text-gray-800">{id}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-gray-400 uppercase">Status</dt>
                <dd className="mt-1">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-0.5 text-xs font-semibold text-green-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                    {state?.status ?? "Complete"}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-gray-400 uppercase">Completed At</dt>
                <dd className="mt-1 text-sm text-gray-700">{formatDate(state?.updated_at)}</dd>
              </div>
            </dl>
          )}
        </div>

        {/* Action buttons */}
        <div className="mt-8 flex flex-col gap-3">
          <p className="text-center text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">
            Next steps
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
            <a
              href={`/e2?session_id=${id}`}
              className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 11h.01M12 11h.01M15 11h.01M4 19V7a2 2 0 012-2h10a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2z" />
              </svg>
              Generate BoM
            </a>
            <a
              href={`/e3?session_id=${id}`}
              className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Generate Proposal
            </a>
            <a
              href={`/e5?session_id=${id}`}
              className="flex items-center justify-center gap-2 rounded-lg bg-purple-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-purple-700"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
              </svg>
              Generate Design
            </a>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center mt-2">
            <a
              href={`/api/e1/${id}/download/matrix`}
              className="flex items-center justify-center gap-2 rounded-lg bg-green-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-green-700"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m0 0l-4-4m4 4l4-4" />
              </svg>
              Download Compliance Matrix
            </a>
            <a
              href={`/e1/${id}/checkpoint2`}
              className="flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Start New Opportunity
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
