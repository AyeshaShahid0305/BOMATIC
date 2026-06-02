"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import DownloadButton from "@/app/components/DownloadButton";
import ReviewBanner from "@/app/components/ReviewBanner";
import RevisionModal from "@/app/components/RevisionModal";

type PackageState = {
  opportunity_id: string;
  project_name: string | null;
  status: string;
  pipeline_step: number;
};

export default function E3ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<PackageState | null>(null);
  const [e3Data, setE3Data] = useState<{section_count: number; ai_generated_count?: number; gbb_tier?: string; total_price?: number} | null>(null);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);
  const [reviewBlocked, setReviewBlocked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [revisionCount, setRevisionCount] = useState(0);
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [revisionSubmitting, setRevisionSubmitting] = useState(false);
  const MAX_REVISIONS = 3;

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

  useEffect(() => {
    fetch(`/api/e3/${encodeURIComponent(id)}/state`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.e3) setE3Data(data.e3);
        if (data?.status === "complete") setApproved(true);
      })
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    fetch(`/api/e1/${encodeURIComponent(id)}/state`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.step_outputs?.revision_counts?.e3 != null) {
          setRevisionCount(data.step_outputs.revision_counts.e3);
        }
      })
      .catch(() => {});
  }, [id]);

  async function handleRevisionSubmit(notes: string) {
    setRevisionSubmitting(true);
    try {
      const res = await fetch(`/api/e3/${encodeURIComponent(id)}/checkpoint/revise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engineer_notes: notes }),
      });
      if (res.status === 409) {
        const b = await res.json();
        setShowRevisionModal(false);
        alert(b.detail ?? "Maximum revisions reached.");
        return;
      }
      if (!res.ok) {
        const b = await res.json();
        throw new Error(b.detail ?? `Error ${res.status}`);
      }
      const data = await res.json();
      setRevisionCount(data.revision_number);
      setShowRevisionModal(false);
      alert(`Revision ${data.revision_number} of ${MAX_REVISIONS} recorded. ${data.message}`);
    } catch (err) {
      setShowRevisionModal(false);
      alert(err instanceof Error ? err.message : "Revision failed.");
    } finally {
      setRevisionSubmitting(false);
    }
  }

  const e3Complete = (state?.pipeline_step ?? 0) >= 22;

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/" className="hover:text-gray-800">BOMATIC</a>
            <span>/</span>
            <a href="/opportunities" className="hover:text-gray-800">Opportunities</a>
            <span>/</span>
            <span className="font-medium text-gray-800">E3 Review</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">E3 Technical Proposal</h1>
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
              {!e3Complete && (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
                  E3 is not complete yet. Generate the technical proposal before downloading output files.
                  <a href={`/e3?session_id=${encodeURIComponent(id)}`} className="ml-1 font-semibold underline">
                    Open Proposal Generator
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        {e3Complete && (
          <ReviewBanner
            opportunityId={id}
            checkpoint="e3"
            onReady={(canApprove) => setReviewBlocked(!canApprove)}
          />
        )}

        {e3Complete && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Downloads
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <DownloadButton
                opportunityId={id}
                filename="technical_proposal.docx"
                label="Download Technical Proposal"
              />
              <DownloadButton opportunityId={id} filename="submission.pdf" label="Download Submission PDF" />
            </div>
          </div>
        )}

        {e3Complete && e3Data && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Proposal Summary</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs text-gray-400">Sections</p>
                <p className="text-xl font-bold text-gray-900">{e3Data.section_count}</p>
              </div>
              {e3Data.gbb_tier && (
                <div>
                  <p className="text-xs text-gray-400">GBB Tier</p>
                  <p className="text-xl font-bold text-gray-900 capitalize">{e3Data.gbb_tier}</p>
                </div>
              )}
              {e3Data.total_price != null && (
                <div>
                  <p className="text-xs text-gray-400">Total Price</p>
                  <p className="text-xl font-bold text-gray-900">
                    {e3Data.total_price.toLocaleString("en-US", { style: "currency", currency: "USD" })}
                  </p>
                </div>
              )}
            </div>
            <div className="mt-5 flex items-center justify-between">
              {approved ? (
                <span className="rounded-full bg-green-100 px-4 py-1.5 text-sm font-semibold text-green-700"> Approved  Complete</span>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="flex flex-col items-end gap-1">
                    {revisionCount > 0 && (
                      <span className="text-xs text-gray-400">
                        Revision {revisionCount} of {MAX_REVISIONS} used
                      </span>
                    )}
                    <button
                      onClick={() => setShowRevisionModal(true)}
                      disabled={approved || revisionCount >= MAX_REVISIONS}
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {revisionCount >= MAX_REVISIONS ? "Max Revisions Reached" : "Request Revision"}
                    </button>
                  </div>
                  <button
                    onClick={async () => {
                      setApproving(true);
                      try {
                        const res = await fetch(`/api/e3/${encodeURIComponent(id)}/checkpoint/approve`, { method: "POST" });
                        if (res.ok) setApproved(true);
                      } finally { setApproving(false); }
                    }}
                    disabled={approving || reviewBlocked}
                    className="rounded-lg bg-green-600 px-5 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    {approving ? "Approving" : "Approve & Mark Complete"}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      {showRevisionModal && (
        <RevisionModal
          engineLabel="E3"
          onClose={() => setShowRevisionModal(false)}
          onSubmit={handleRevisionSubmit}
          submitting={revisionSubmitting}
        />
      )}
    </main>
  );
}
