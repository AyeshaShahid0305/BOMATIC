"use client";
import { useState } from "react";

const SEVERITY_RANK = { critical: 3, high: 2, medium: 1, low: 0 };

const SEVERITY_CLS = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-amber-100 text-amber-700 border-amber-200",
  low:      "bg-gray-100 text-gray-600 border-gray-200",
};

const CLASS_CLS = {
  mandatory:   "bg-green-100 text-green-700 border-green-200",
  conditional: "bg-purple-100 text-purple-700 border-purple-200",
  optional:    "bg-blue-100 text-blue-700 border-blue-200",
};

function SeverityBadge({ severity }) {
  const cls = SEVERITY_CLS[severity] ?? "bg-gray-100 text-gray-600 border-gray-200";
  return (
    <span className={`shrink-0 px-2 py-0.5 rounded border text-xs font-semibold uppercase ${cls}`}>
      {severity}
    </span>
  );
}

function ClassBadge({ type }) {
  const cls = CLASS_CLS[type] ?? "bg-gray-100 text-gray-600 border-gray-200";
  return (
    <span className={`shrink-0 px-2 py-0.5 rounded border text-xs font-semibold uppercase ${cls}`}>
      {type}
    </span>
  );
}

function MetricCard({ label, value, alert }) {
  return (
    <div className={`rounded-lg border p-4 text-center ${alert ? "border-red-200 bg-red-50" : "border-gray-200 bg-white"}`}>
      <p className={`text-3xl font-bold ${alert ? "text-red-600" : "text-gray-900"}`}>{value}</p>
      <p className="mt-1 text-sm text-gray-500">{label}</p>
    </div>
  );
}

export default function E1Checkpoint({ result, onProceed }) {
  const [held, setHeld] = useState(false);

  const files       = result.files        ?? [];
  const requirements = result.requirements ?? [];
  const flags       = [...(result.flags   ?? [])].sort(
    (a, b) => (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0),
  );
  const missingDocs = result.missing_docs  ?? [];

  const hasCritical = flags.some((f) => f.severity === "critical");

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">E1 Analysis — Human Checkpoint</h1>
        {held && (
          <span className="rounded-full border border-yellow-300 bg-yellow-100 px-3 py-1 text-sm font-medium text-yellow-800">
            Bid on Hold
          </span>
        )}
      </div>

      {/* Hold banner */}
      {held && (
        <div className="flex items-center gap-3 rounded-lg border border-yellow-300 bg-yellow-50 p-4">
          <span className="text-xl text-yellow-500">⚠</span>
          <p className="text-sm font-medium text-yellow-800">
            This bid is on hold. Review all risk flags and missing documents before proceeding.
          </p>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard label="Files Analyzed"  value={files.length}       />
        <MetricCard label="Requirements"    value={requirements.length} />
        <MetricCard label="Risk Flags"      value={flags.length}       alert={hasCritical} />
        <MetricCard label="Missing Docs"    value={missingDocs.length} />
      </div>

      {/* Risk Flags */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-800">Risk Flags</h2>
        {flags.length === 0 ? (
          <p className="text-sm text-gray-500">No risk flags detected.</p>
        ) : (
          <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
            {flags.map((f, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3">
                <SeverityBadge severity={f.severity} />
                <span className="flex-1 text-sm font-medium text-gray-800">
                  {f.flag.replace(/_/g, " ")}
                </span>
                {f.deadline && (
                  <span className="rounded border border-gray-200 bg-gray-50 px-2 py-0.5 font-mono text-xs text-gray-600">
                    {f.deadline}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Requirements */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-800">Requirements</h2>
        {requirements.length === 0 ? (
          <p className="text-sm text-gray-500">No requirements extracted.</p>
        ) : (
          <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
            {requirements.map((r, i) => (
              <div key={i} className="flex items-start gap-3 px-4 py-3">
                <span className="mt-0.5 w-9 shrink-0 font-mono text-xs text-gray-400">
                  {(r.confidence * 100).toFixed(0) + '%'}
                </span>
                <ClassBadge type={r.type} />
                <p className="flex-1 text-sm text-gray-700">{r.text}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Missing Docs */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-800">Missing Documents</h2>
        {missingDocs.length === 0 ? (
          <p className="text-sm text-gray-500">No missing documents detected.</p>
        ) : (
          <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
            {missingDocs.map((d, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3">
                <SeverityBadge severity={d.severity} />
                <span className="flex-1 text-sm font-medium text-gray-800">{d.name}</span>
                <span className="text-xs text-gray-500">{d.action}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Files Analyzed */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-800">Files Analyzed</h2>
        <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <span className="flex-1 text-sm text-gray-700">{f.name}</span>
              <span className="rounded border border-gray-200 bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-600">
                {f.type}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button
          onClick={() => setHeld(true)}
          disabled={held}
          className="rounded-lg border border-yellow-400 bg-yellow-50 px-5 py-2.5 text-sm font-medium text-yellow-800 transition-colors hover:bg-yellow-100 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Hold Bid
        </button>
        <button
          onClick={onProceed}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Proceed to Step 5
        </button>
      </div>

    </div>
  );
}
