"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import DownloadButton from "@/app/components/DownloadButton";

type PackageState = {
  opportunity_id: string;
  project_name: string | null;
  status: string;
  pipeline_step: number;
};

export default function E1CompletePage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<PackageState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/v1/rfp/packages/${encodeURIComponent(id)}`)
      .then(async response => {
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw new Error(body?.detail ?? `Failed to load opportunity (${response.status})`);
        }
        return response.json();
      })
      .then(setState)
      .catch(err => setError(err instanceof Error ? err.message : "Failed to load opportunity."))
      .finally(() => setLoading(false));
  }, [id]);

  const e1Complete = (state?.pipeline_step ?? 0) >= 12;

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/" className="hover:text-gray-800">BOMATIC</a>
            <span>/</span>
            <a href="/opportunities" className="hover:text-gray-800">Opportunities</a>
            <span>/</span>
            <span className="font-medium text-gray-800">E1 Complete</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">E1 Compliance Matrix</h1>
          <p className="mt-1 text-sm text-gray-500">Opportunity {id}</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          {loading && <p className="text-sm text-gray-500">Loading opportunity...</p>}
          {error && <p className="text-sm text-red-700">{error}</p>}
          {!loading && !error && (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Project</p>
                <p className="mt-1 text-lg font-semibold text-gray-900">
                  {state?.project_name || "Untitled project"}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Current step</p>
                <p className="mt-1 text-sm font-semibold text-gray-800">Step {state?.pipeline_step ?? 0}</p>
              </div>
              {!e1Complete && (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
                  E1 is not complete yet. Run the E1 pipeline before downloading.
                  <a href="/e1/upload" className="ml-1 font-semibold underline">
                    Open E1 Upload
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        {e1Complete && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Downloads
            </h2>
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
          </div>
        )}
      </div>
    </main>
  );
}
