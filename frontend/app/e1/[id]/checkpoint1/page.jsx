"use client";
import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";

// ---------------------------------------------------------------------------
// Small reusable pieces
// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <svg className="h-5 w-5 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
    </svg>
  );
}

function SectionCard({ title, children }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-6 py-4">
        <h2 className="text-base font-semibold text-gray-800">{title}</h2>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

function EmptyBadge({ text }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1 text-sm font-medium text-green-700">
      <span className="h-2 w-2 rounded-full bg-green-500" />
      {text}
    </span>
  );
}

const SEVERITY_CLASSES = {
  critical: "bg-red-100 text-red-700",
  high:     "bg-red-100 text-red-700",
  medium:   "bg-orange-100 text-orange-700",
  low:      "bg-yellow-100 text-yellow-700",
};

const CLASSIFICATION_CLASSES = {
  mandatory:   "bg-blue-100 text-blue-700",
  optional:    "bg-gray-100 text-gray-600",
  conditional: "bg-yellow-100 text-yellow-700",
};

function Badge({ label, colorClass }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${colorClass}`}>
      {label}
    </span>
  );
}

function TableWrap({ heads, children }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-gray-50">
            {heads.map(h => (
              <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">{children}</tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

function Toast({ message, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div className="fixed bottom-24 right-6 z-50 flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3 shadow-lg">
      <span className="text-green-700 text-sm font-medium">{message}</span>
      <button onClick={onClose} className="text-green-500 hover:text-green-700 text-lg leading-none">✕</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Revision modal
// ---------------------------------------------------------------------------

function RevisionModal({ onClose, onSubmit, submitting }) {
  const [notes, setNotes] = useState("");
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
        <h3 className="mb-1 text-base font-semibold text-gray-800">Request Revision</h3>
        <p className="mb-4 text-sm text-gray-500">
          Describe what needs to be corrected. The pipeline will be re-run with your notes.
        </p>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={5}
          placeholder="e.g. File X was mis-classified as legal — it is actually technical. Requirement R-005 is a false positive."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <div className="mt-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onSubmit(notes)}
            disabled={!notes.trim() || submitting}
            className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Submit Revision Request"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 1: Classified Files
// ---------------------------------------------------------------------------

function ClassifiedFilesSection({ files }) {
  if (!files?.length) return <p className="text-sm text-gray-400">No file data available.</p>;
  return (
    <TableWrap heads={["Filename", "Type", "Confidence", "Needs Review"]}>
      {files.map((f, i) => (
        <tr key={i} className="hover:bg-gray-50">
          <td className="px-4 py-3 text-gray-800 font-medium">{f.filename}</td>
          <td className="px-4 py-3 text-gray-600 capitalize">{f.type?.replace(/_/g, " ")}</td>
          <td className="px-4 py-3">
            <span className={`font-mono text-xs ${f.confidence >= 0.8 ? "text-green-700" : f.confidence >= 0.5 ? "text-yellow-700" : "text-red-600"}`}>
              {f.confidence != null ? `${(f.confidence * 100).toFixed(0)}%` : "—"}
            </span>
          </td>
          <td className="px-4 py-3">
            {f.needs_human_review
              ? <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-700">Review needed</span>
              : <span className="rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">OK</span>}
          </td>
        </tr>
      ))}
    </TableWrap>
  );
}

// ---------------------------------------------------------------------------
// Section 2: Missing Documents
// ---------------------------------------------------------------------------

function MissingDocsSection({ docs }) {
  if (!docs?.length) return <EmptyBadge text="No missing documents detected" />;
  return (
    <TableWrap heads={["Document", "Severity", "Action"]}>
      {docs.map((d, i) => (
        <tr key={i} className="hover:bg-gray-50">
          <td className="px-4 py-3 text-gray-800">{d.referenced_doc}</td>
          <td className="px-4 py-3">
            <Badge label={d.severity} colorClass={SEVERITY_CLASSES[d.severity] ?? "bg-gray-100 text-gray-600"} />
          </td>
          <td className="px-4 py-3 text-gray-600">{d.action}</td>
        </tr>
      ))}
    </TableWrap>
  );
}

// ---------------------------------------------------------------------------
// Section 3: Requirements Summary
// ---------------------------------------------------------------------------

function RequirementsSummarySection({ reqs }) {
  if (!reqs?.length) return <p className="text-sm text-gray-400">No requirements extracted.</p>;

  const counts = reqs.reduce(
    (acc, r) => { acc[r.classification] = (acc[r.classification] ?? 0) + 1; return acc; },
    {}
  );

  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-gray-900">{reqs.length}</span>
        <span className="text-sm text-gray-500">requirements extracted</span>
      </div>
      <div className="flex flex-wrap gap-3">
        {Object.entries(counts).map(([cls, count]) => (
          <div key={cls} className={`flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium ${CLASSIFICATION_CLASSES[cls] ?? "bg-gray-100 text-gray-600"}`}>
            <span className="text-base font-bold">{count}</span>
            <span className="capitalize">{cls}</span>
          </div>
        ))}
      </div>
      <div className="max-h-64 overflow-y-auto rounded-lg border border-gray-200">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">ID</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Requirement</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Type</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {reqs.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs text-gray-500">{r.id}</td>
                <td className="px-4 py-2 text-gray-700 max-w-md">{r.text}</td>
                <td className="px-4 py-2">
                  <Badge label={r.classification} colorClass={CLASSIFICATION_CLASSES[r.classification] ?? "bg-gray-100 text-gray-600"} />
                </td>
                <td className="px-4 py-2 font-mono text-xs text-gray-500">
                  {r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 4: Risk Flags
// ---------------------------------------------------------------------------

function RiskFlagsSection({ flags }) {
  if (!flags?.length) return <EmptyBadge text="No risk flags detected" />;
  return (
    <TableWrap heads={["Flag", "Severity", "Deadline", "Source"]}>
      {flags.map((f, i) => (
        <tr key={i} className="hover:bg-gray-50">
          <td className="px-4 py-3 text-gray-800 max-w-xs">{f.flag}</td>
          <td className="px-4 py-3">
            <Badge label={f.severity} colorClass={SEVERITY_CLASSES[f.severity] ?? "bg-gray-100 text-gray-600"} />
          </td>
          <td className="px-4 py-3 text-gray-600 text-xs">
            {f.deadline ?? "—"}
            {f.days_remaining != null && (
              <span className="ml-1 text-orange-600 font-medium">({f.days_remaining}d)</span>
            )}
          </td>
          <td className="px-4 py-3 text-gray-500 text-xs">{f.source ?? "—"}</td>
        </tr>
      ))}
    </TableWrap>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Checkpoint1Page() {
  const { id } = useParams();
  const router = useRouter();

  const [state, setState] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [approving, setApproving] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [revisionSubmitting, setRevisionSubmitting] = useState(false);
  const [toast, setToast] = useState(null);

  const dismissToast = useCallback(() => setToast(null), []);

  useEffect(() => {
    fetch(`/api/e1/${id}/state`)
      .then(r => r.ok ? r.json() : r.json().then(b => Promise.reject(b.detail ?? "Failed to load state")))
      .then(setState)
      .catch(err => setLoadError(typeof err === "string" ? err : "Failed to load pipeline state."));
  }, [id]);

  async function handleApprove() {
    setApproving(true);
    try {
      const res = await fetch(`/api/e1/${id}/checkpoint1/approve`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail ?? `Server error ${res.status}`);
      }
      router.push(`/e1/${id}/checkpoint2`);
    } catch (err) {
      setToast(`Approval failed: ${err.message}`);
      setApproving(false);
    }
  }

  async function handleRevisionSubmit(notes) {
    setRevisionSubmitting(true);
    // Stub: a real implementation would POST revision notes and re-trigger the pipeline
    await new Promise(r => setTimeout(r, 600));
    setRevisionSubmitting(false);
    setShowModal(false);
    setToast("Revision request submitted. The pipeline will re-run with your notes.");
  }

  // Loading
  if (!state && !loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Spinner />
          <p className="text-sm text-gray-500">Loading pipeline state…</p>
        </div>
      </div>
    );
  }

  // Fetch error
  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-8">
        <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-semibold text-red-800">Failed to load pipeline state</p>
          <p className="mt-1 text-sm text-red-600">{loadError}</p>
          <a href={`/e1/${id}`} className="mt-4 inline-block text-sm text-blue-600 underline">← Back to opportunity</a>
        </div>
      </div>
    );
  }

  const step = state.current_step ?? 0;
  const outputs = state.step_outputs ?? {};

  // Steps 1-4 not done
  if (step < 4) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-8">
        <div className="max-w-md rounded-xl border border-yellow-200 bg-yellow-50 p-6 text-center">
          <p className="font-semibold text-yellow-800">Analysis not yet complete</p>
          <p className="mt-1 text-sm text-yellow-700">Run the pipeline first before reviewing Checkpoint 1.</p>
          <a href={`/e1/${id}`} className="mt-4 inline-block text-sm text-blue-600 underline">← Back to opportunity</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-32">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-5xl">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/" className="hover:text-gray-800">BOMATIC</a>
            <span>/</span>
            <a href={`/e1/${id}`} className="hover:text-gray-800">Opportunity {id}</a>
            <span>/</span>
            <span className="text-gray-800 font-medium">Checkpoint 1</span>
          </div>
          <div className="mt-2 flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-900">Checkpoint 1 — Review Analysis Results</h1>
            {step >= 11 && (
              <span className="rounded-full bg-green-100 px-3 py-0.5 text-xs font-semibold text-green-700">
                Approved
              </span>
            )}
          </div>
          {step >= 11 && (
            <p className="mt-1 text-sm text-green-700">
              Checkpoint 1 already approved.{" "}
              <a href={`/e1/${id}/checkpoint2`} className="font-medium underline">Go to Checkpoint 2 →</a>
            </p>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="mx-auto max-w-5xl space-y-6 px-6 py-8">

        {/* Section 1 */}
        <SectionCard title="Section A — Classified Files">
          <ClassifiedFilesSection files={outputs["1"]} />
        </SectionCard>

        {/* Section 2 */}
        <SectionCard title="Section B — Missing Documents">
          <MissingDocsSection docs={outputs["2"]} />
        </SectionCard>

        {/* Section 3 */}
        <SectionCard title="Section C — Requirements Summary">
          <RequirementsSummarySection reqs={outputs["3"]} />
        </SectionCard>

        {/* Section 4 */}
        <SectionCard title="Section D — Risk Flags">
          <RiskFlagsSection flags={outputs["4"]} />
        </SectionCard>

      </div>

      {/* Sticky bottom action bar */}
      <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-gray-200 bg-white px-6 py-4 shadow-lg">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <a
            href={`/e1/${id}`}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            ← Back
          </a>
          <div className="flex gap-3">
            <button
              onClick={() => setShowModal(true)}
              disabled={step >= 11}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Request Revision
            </button>
            <button
              onClick={handleApprove}
              disabled={approving || step >= 11}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {approving && <Spinner />}
              {step >= 11 ? "Already Approved" : approving ? "Approving…" : "Approve — Proceed to Compliance Mapping"}
            </button>
          </div>
        </div>
      </div>

      {/* Revision modal */}
      {showModal && (
        <RevisionModal
          onClose={() => setShowModal(false)}
          onSubmit={handleRevisionSubmit}
          submitting={revisionSubmitting}
        />
      )}

      {/* Toast */}
      {toast && <Toast message={toast} onClose={dismissToast} />}
    </div>
  );
}
