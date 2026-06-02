"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import DownloadButton from "@/app/components/DownloadButton";
import ReviewBanner from "@/app/components/ReviewBanner";
import RevisionModal from "@/app/components/RevisionModal";

type E4Data = {
  project_name: string;
  total_questions: number;
  categories: string[];
  must_have_count: number;
  nice_to_have_count: number;
  output_file: string;
};

type E4State = {
  opportunity_id: string;
  project_name: string | null;
  status: string;
  current_step: number;
  e4: E4Data;
};

function Spinner() {
  return (
    <svg className="h-5 w-5 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

export default function E4CheckpointPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<E4State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);
  const [reviewBlocked, setReviewBlocked] = useState(false);
  const [revisionCount, setRevisionCount] = useState(0);
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [revisionSubmitting, setRevisionSubmitting] = useState(false);
  const MAX_REVISIONS = 3;

  useEffect(() => {
    fetch(`/api/e4/${encodeURIComponent(id)}/state`)
      .then(async r => {
        if (!r.ok) {
          const b = await r.json().catch(() => null);
          throw new Error(b?.detail ?? `Error ${r.status}`);
        }
        return r.json();
      })
      .then(data => {
        setState(data);
        if (data.status === "e4_approved") setApproved(true);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    fetch(`/api/e1/${encodeURIComponent(id)}/state`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.step_outputs?.revision_counts?.e4 != null) {
          setRevisionCount(data.step_outputs.revision_counts.e4);
        }
      })
      .catch(() => {});
  }, [id]);

  async function handleApprove() {
    setApproving(true);
    try {
      const res = await fetch(`/api/e4/${encodeURIComponent(id)}/checkpoint/approve`, { method: "POST" });
      if (!res.ok) {
        const b = await res.json();
        throw new Error(b.detail ?? `Error ${res.status}`);
      }
      setApproved(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Approval failed.");
    } finally {
      setApproving(false);
    }
  }

  async function handleRevisionSubmit(notes: string) {
    setRevisionSubmitting(true);
    try {
      const res = await fetch(`/api/e4/${encodeURIComponent(id)}/checkpoint/revise`, {
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

  const e4 = state?.e4;

  return (
    <main className="min-h-screen bg-gray-50 pb-28 px-6 py-10">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/" className="hover:text-gray-800">BOMATIC</a>
            <span>/</span>
            <a href="/opportunities" className="hover:text-gray-800">Opportunities</a>
            <span>/</span>
            <span className="font-medium text-gray-800">E4 Checkpoint</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">E4  RFI Questionnaire Review</h1>
          <p className="mt-1 text-sm text-gray-500">Opportunity {id}</p>
        </div>

        {loading && <p className="text-sm text-gray-400">Loading</p>}
        {error && <p className="text-sm text-red-700">{error}</p>}

        {!loading && !error && e4 && (
          <>
            <ReviewBanner
              opportunityId={id}
              checkpoint="e4"
              onReady={(canApprove) => setReviewBlocked(!canApprove)}
            />

            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Total Questions</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{e4.total_questions}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Must-Have</p>
                <p className="mt-1 text-2xl font-bold text-blue-700">{e4.must_have_count}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Nice-to-Have</p>
                <p className="mt-1 text-2xl font-bold text-gray-600">{e4.nice_to_have_count}</p>
              </div>
            </div>

            {e4.categories.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Categories</p>
                <div className="flex flex-wrap gap-2">
                  {e4.categories.map((c: string) => (
                    <span key={c} className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700">{c}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Downloads</p>
              <DownloadButton opportunityId={id} filename="rfi_questionnaire.xlsx" label="Download RFI Questionnaire" />
            </div>

            {approved && (
              <div className="rounded-xl border border-green-200 bg-green-50 px-5 py-4 text-sm font-medium text-green-800">
                 E4 approved. <a href={`/e5?session_id=${encodeURIComponent(id)}`} className="underline font-semibold">Generate the HLD/LLD Design </a>
              </div>
            )}
          </>
        )}
      </div>

      {!loading && !error && e4 && (
        <div className="fixed bottom-0 left-0 right-0 border-t border-gray-200 bg-white px-6 py-4 shadow-lg">
          <div className="mx-auto flex max-w-3xl items-center justify-between">
            <a href="/opportunities" className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
               Opportunities
            </a>
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
                onClick={handleApprove}
                disabled={approving || approved || reviewBlocked}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {approving && <Spinner />}
                {approved ? "Approved" : approving ? "Approving" : "Approve & Continue to E5"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showRevisionModal && (
        <RevisionModal
          engineLabel="E4"
          onClose={() => setShowRevisionModal(false)}
          onSubmit={handleRevisionSubmit}
          submitting={revisionSubmitting}
        />
      )}
    </main>
  );
}
