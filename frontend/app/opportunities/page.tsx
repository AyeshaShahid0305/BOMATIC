"use client";

import { useEffect, useMemo, useState } from "react";

type OpportunityMode = "rfp" | "rfi";

type Opportunity = {
  opportunity_id: string | null;
  project_name: string | null;
  client_name: string | null;
  mode?: OpportunityMode | null;
  status: string;
  current_step: number;
  created_at: string;
  engines_completed: string[];
};

const VALID_STATUS_STYLES: Record<string, string> = {
  e1_pending: "bg-blue-100 text-blue-700",
  e1_complete: "bg-green-100 text-green-700",
  e2_pending: "bg-teal-100 text-teal-700",
  e2_complete: "bg-green-100 text-green-700",
  e3_pending: "bg-purple-100 text-purple-700",
  e3_complete: "bg-green-100 text-green-700",
  e4_pending: "bg-orange-100 text-orange-700",
  e4_complete: "bg-green-100 text-green-700",
  e5_pending: "bg-indigo-100 text-indigo-700",
  e5_complete: "bg-green-100 text-green-700",
};

const statusStyles: Record<string, string> = {
  ...VALID_STATUS_STYLES,
  uploaded: "bg-gray-100 text-gray-700",
  checkpoint_1_pending: "bg-blue-100 text-blue-700",
  checkpoint_2_pending: "bg-yellow-100 text-yellow-700",
  complete: "bg-green-100 text-green-700",
};

const modeStyles: Record<OpportunityMode, string> = {
  rfp: "bg-blue-50 text-blue-700 border-blue-200",
  rfi: "bg-orange-50 text-orange-700 border-orange-200",
};

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function engineLink(opportunity: Opportunity) {
  const id = opportunity.opportunity_id;
  const mode = opportunity.mode ?? "rfp";
  const step = opportunity.current_step ?? 0;

  if (!id) return mode === "rfi" ? "/e4" : "/e1/upload";

  if (mode === "rfi") {
    if (step < 4) return `/e4/${id}`;
    if (step <= 10) return `/e4/${id}/checkpoint${step}`;
    if (step === 11) return `/e5/${id}`;
    if (step <= 20) return `/e5/${id}/checkpoint${step}`;
    if (step === 21) return `/e2/${id}`;
    return `/e3/${id}`;
  }

  if (step < 4) return "/e1/upload";
  if (step < 11) return `/e1/${id}/checkpoint1`;
  if (step <= 11) return `/e1/${id}/checkpoint2`;
  if (step === 12) return `/e2/${id}`;
  if (step <= 20) return `/e2/${id}/checkpoint${step}`;
  if (step === 21) return `/e3/${id}`;
  return `/e3/${id}/review`;
}

function Spinner() {
  return (
    <svg className="h-5 w-5 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/opportunities")
      .then(async response => {
        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || `Failed to load opportunities: ${response.status}`);
        }
        return response.json();
      })
      .then(data => setOpportunities(Array.isArray(data) ? data : []))
      .catch(err => setError(err.message || "Failed to load opportunities."))
      .finally(() => setLoading(false));
  }, []);

  const totalCompleted = useMemo(
    () => opportunities.filter(item => item.status.endsWith("_complete")).length,
    [opportunities]
  );

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <a href="/" className="hover:text-gray-800">BOMATIC</a>
              <span>/</span>
              <span className="font-medium text-gray-800">Opportunities</span>
            </div>
            <h1 className="mt-2 text-3xl font-bold text-gray-900">Opportunities</h1>
            <p className="mt-1 text-gray-500">All RFP and RFI sessions with their pipeline progress.</p>
          </div>
          <a
            href="/e1/upload"
            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            New Session
          </a>
        </div>

        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Total sessions</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">{opportunities.length}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Completed</p>
            <p className="mt-2 text-3xl font-bold text-green-700">{totalCompleted}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">In progress</p>
            <p className="mt-2 text-3xl font-bold text-blue-700">{opportunities.length - totalCompleted}</p>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center gap-3 rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
            <Spinner />
            <p className="text-sm text-gray-500">Loading opportunities...</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && opportunities.length === 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
            <h2 className="text-lg font-semibold text-gray-800">No opportunities yet</h2>
            <p className="mt-1 text-sm text-gray-500">Upload an RFP or RFI package to start your first session.</p>
            <a
              href="/e1/upload"
              className="mt-5 inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Upload Package
            </a>
          </div>
        )}

        {!loading && !error && opportunities.length > 0 && (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {opportunities.map(opportunity => {
              const id = opportunity.opportunity_id ?? "Unknown";
              const mode = opportunity.mode ?? "rfp";
              const link = engineLink(opportunity);
              const completed = opportunity.engines_completed ?? [];
              const statusClass = statusStyles[opportunity.status];

              return (
                <div key={id} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h2 className="truncate text-lg font-semibold text-gray-900">
                        {opportunity.project_name || "Untitled project"}
                      </h2>
                      <p className="mt-1 text-sm text-gray-500">
                        {opportunity.client_name || "No client name"}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase ${modeStyles[mode]}`}>
                        {mode}
                      </span>
                      <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${statusClass ?? "bg-red-100 text-red-700"}`}>
                        {formatLabel(opportunity.status)}
                      </span>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div>
                      <p className="text-xs font-medium uppercase text-gray-400">Opportunity ID</p>
                      <p className="mt-1 truncate font-mono text-sm text-gray-700">{id}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase text-gray-400">Current step</p>
                      <p className="mt-1 text-sm font-semibold text-gray-800">Step {opportunity.current_step}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase text-gray-400">Created</p>
                      <p className="mt-1 text-sm text-gray-700">{formatDate(opportunity.created_at)}</p>
                    </div>
                  </div>

                  <div className="mt-5">
                    <p className="text-xs font-medium uppercase text-gray-400">Engines completed</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {completed.length > 0 ? completed.map(engine => (
                        <span key={engine} className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                          {engine}
                        </span>
                      )) : (
                        <span className="text-sm text-gray-400">No completed outputs yet</span>
                      )}
                    </div>
                  </div>

                  <a
                    href={link}
                    className="mt-6 block w-full rounded-lg bg-blue-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-blue-700"
                  >
                    Open Relevant Engine Page
                  </a>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
