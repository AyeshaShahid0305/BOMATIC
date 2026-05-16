"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";

// ---------------------------------------------------------------------------
// Shared primitives (same visual language as checkpoint1)
// ---------------------------------------------------------------------------

function Spinner({ small = false }) {
  return (
    <svg
      className={`animate-spin text-current ${small ? "h-3.5 w-3.5" : "h-5 w-5 text-blue-600"}`}
      viewBox="0 0 24 24" fill="none"
    >
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

// ---------------------------------------------------------------------------
// Status config
// ---------------------------------------------------------------------------

const STATUS_OPTIONS = ["Compliant", "Partial", "Non-Compliant", "Alternative Offered"];

const STATUS_STYLES = {
  "Compliant":          { select: "bg-green-50  text-green-800  border-green-200",  badge: "bg-green-100  text-green-700" },
  "Partial":            { select: "bg-yellow-50 text-yellow-800 border-yellow-200", badge: "bg-yellow-100 text-yellow-700" },
  "Non-Compliant":      { select: "bg-red-50    text-red-800    border-red-200",    badge: "bg-red-100    text-red-700" },
  "Alternative Offered":{ select: "bg-blue-50   text-blue-800   border-blue-200",   badge: "bg-blue-100   text-blue-700" },
};

const GAP_STYLES = {
  none:            "bg-gray-100  text-gray-500",
  coverage_gap:    "bg-orange-100 text-orange-700",
  orphan:          "bg-red-100   text-red-700",
};

const GAP_LABELS = {
  none:         "None",
  coverage_gap: "Coverage Gap",
  orphan:       "Orphan",
};

const CLASSIFICATION_STYLES = {
  mandatory:   "bg-blue-100   text-blue-700",
  optional:    "bg-gray-100   text-gray-500",
  conditional: "bg-yellow-100 text-yellow-700",
};

function Badge({ label, colorClass }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${colorClass}`}>
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Stats bar
// ---------------------------------------------------------------------------

function StatCard({ label, value, color }) {
  const bg = {
    green:  "bg-green-50  border-green-200  text-green-700",
    yellow: "bg-yellow-50 border-yellow-200 text-yellow-700",
    red:    "bg-red-50    border-red-200    text-red-700",
    blue:   "bg-blue-50   border-blue-200   text-blue-700",
    grey:   "bg-gray-50   border-gray-200   text-gray-600",
    white:  "bg-white     border-gray-200   text-gray-800",
  }[color] ?? "bg-white border-gray-200 text-gray-800";

  return (
    <div className={`flex flex-col items-center rounded-xl border px-4 py-3 min-w-[90px] ${bg}`}>
      <span className="text-2xl font-bold">{value ?? 0}</span>
      <span className="mt-0.5 text-xs font-medium text-center leading-tight">{label}</span>
    </div>
  );
}

function StatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div className="flex flex-wrap gap-3">
      <StatCard label="Total Requirements"  value={stats.total_reqs}       color="white"  />
      <StatCard label="Compliant"           value={stats.compliant}        color="green"  />
      <StatCard label="Partial"             value={stats.partial}          color="yellow" />
      <StatCard label="Non-Compliant"       value={stats.non_compliant}    color="red"    />
      <StatCard label="Alternative Offered" value={stats.alternative}      color="blue"   />
      <StatCard label="Orphan Requirements" value={stats.orphans}          color="grey"   />
      <StatCard label="Coverage Gaps"       value={stats.coverage_gaps}    color="grey"   />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toast with download link
// ---------------------------------------------------------------------------

function Toast({ message, downloadUrl, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 8000);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div className="fixed bottom-24 right-6 z-50 max-w-sm rounded-xl border border-green-200 bg-green-50 p-4 shadow-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-green-800">{message}</p>
          {downloadUrl && (
            <a
              href={downloadUrl}
              className="mt-1 inline-block text-sm font-medium text-blue-600 underline"
              target="_blank" rel="noreferrer"
            >
              Download Compliance Matrix (.xlsx)
            </a>
          )}
        </div>
        <button onClick={onClose} className="text-green-500 hover:text-green-700 text-lg leading-none shrink-0">✕</button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editable matrix row
// ---------------------------------------------------------------------------

function MatrixRow({ row, onStatusChange, onNotesChange, saving, expanded, onToggleExpand }) {
  const statusStyle = STATUS_STYLES[row.status] ?? {};
  const gapClass = GAP_STYLES[row.gap_type] ?? GAP_STYLES.none;
  const gapLabel = GAP_LABELS[row.gap_type] ?? row.gap_type;

  return (
    <tr className="hover:bg-gray-50 align-top">
      {/* Req # */}
      <td className="px-3 py-3 font-mono text-xs text-gray-500 whitespace-nowrap">{row.req_id}</td>

      {/* Requirement Text */}
      <td className="px-3 py-3 text-sm text-gray-700 max-w-xs">
        <div className={expanded ? "" : "line-clamp-2"}>{row.req_text}</div>
        <button
          onClick={onToggleExpand}
          className="mt-0.5 text-xs text-blue-500 hover:text-blue-700"
        >
          {expanded ? "show less" : "show more"}
        </button>
      </td>

      {/* Classification */}
      <td className="px-3 py-3">
        <Badge
          label={row.classification}
          colorClass={CLASSIFICATION_STYLES[row.classification] ?? "bg-gray-100 text-gray-600"}
        />
      </td>

      {/* Framework */}
      <td className="px-3 py-3 text-xs text-gray-500 whitespace-nowrap">{row.framework || "—"}</td>

      {/* Control ID */}
      <td className="px-3 py-3 font-mono text-xs text-gray-500 whitespace-nowrap">{row.control_id || "—"}</td>

      {/* Control Name */}
      <td className="px-3 py-3 text-xs text-gray-600 max-w-[160px]">{row.control_name || "—"}</td>

      {/* Status — editable dropdown */}
      <td className="px-3 py-3">
        {row.gap_type === "orphan" ? (
          <span className="text-xs text-gray-400 italic">N/A</span>
        ) : (
          <select
            value={row.status}
            onChange={e => onStatusChange(e.target.value)}
            className={`rounded-md border px-2 py-1 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 ${statusStyle.select ?? "bg-white border-gray-300 text-gray-700"}`}
          >
            {STATUS_OPTIONS.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        )}
      </td>

      {/* TP Section */}
      <td className="px-3 py-3 text-xs text-gray-600 whitespace-nowrap">{row.tp_section || "—"}</td>

      {/* Notes — editable input */}
      <td className="px-3 py-3">
        <div className="relative flex items-center gap-1">
          <input
            type="text"
            value={row.notes ?? ""}
            onChange={e => onNotesChange(e.target.value)}
            placeholder="Add note…"
            className="w-36 rounded border border-gray-200 px-2 py-1 text-xs text-gray-700 placeholder-gray-400 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          {saving && <Spinner small />}
        </div>
      </td>

      {/* Gap Type */}
      <td className="px-3 py-3">
        <Badge label={gapLabel} colorClass={gapClass} />
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Gap Analysis section
// ---------------------------------------------------------------------------

function GapAnalysis({ gaps }) {
  const coverageGaps = gaps?.coverage_gaps ?? [];
  const orphans = gaps?.orphan_requirements ?? [];

  if (!coverageGaps.length && !orphans.length) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 px-5 py-4">
        <span className="h-2.5 w-2.5 rounded-full bg-green-500 shrink-0" />
        <span className="text-sm font-medium text-green-800">
          No gaps detected — full coverage achieved
        </span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Coverage Gaps */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-gray-700">
          Coverage Gaps
          <span className="ml-2 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700">
            {coverageGaps.length}
          </span>
        </h3>
        {coverageGaps.length === 0 ? (
          <p className="text-sm text-gray-400">None</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Framework", "Control ID", "Control Name"].map(h => (
                    <th key={h} className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {coverageGaps.map((g, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-xs text-gray-500">{g.framework}</td>
                    <td className="px-3 py-2 font-mono text-xs text-gray-500">{g.control_id}</td>
                    <td className="px-3 py-2 text-xs text-gray-700">{g.control_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Orphan Requirements */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-gray-700">
          Orphan Requirements
          <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            {orphans.length}
          </span>
        </h3>
        {orphans.length === 0 ? (
          <p className="text-sm text-gray-400">None</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Req #", "Requirement Text", "Classification"].map(h => (
                    <th key={h} className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {orphans.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-mono text-xs text-gray-500">{r.req_id}</td>
                    <td className="px-3 py-2 text-xs text-gray-700 max-w-xs">{r.req_text}</td>
                    <td className="px-3 py-2">
                      <Badge label={r.classification} colorClass={CLASSIFICATION_STYLES[r.classification] ?? "bg-gray-100 text-gray-600"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Checkpoint2Page() {
  const { id } = useParams();
  const router = useRouter();

  const [rows, setRows]       = useState([]);
  const [gaps, setGaps]       = useState(null);
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [savingRows, setSavingRows] = useState({});   // rowIndex → true/false
  const [approving, setApproving]   = useState(false);
  const [toast, setToast]           = useState(null);
  const [expandedRows, setExpandedRows] = useState({});

  const saveTimers = useRef({});
  const dismissToast = useCallback(() => setToast(null), []);

  // Fetch matrix on mount
  useEffect(() => {
    fetch(`/api/e1/${id}/matrix`)
      .then(r => {
        if (r.status === 404) throw new Error("404");
        if (!r.ok) return r.json().then(b => Promise.reject(b.detail ?? "Failed to load matrix"));
        return r.json();
      })
      .then(data => {
        setRows(data.matrix_rows ?? []);
        setGaps(data.gaps ?? {});
        setStats(data.stats ?? {});
        setLoading(false);
      })
      .catch(err => {
        setLoadError(err.message === "404" ? "404" : (err.message || "Failed to load matrix."));
        setLoading(false);
      });
  }, [id]);

  // Debounced save for a single row
  function scheduleSave(rowIndex, updatedRow) {
    if (saveTimers.current[rowIndex]) clearTimeout(saveTimers.current[rowIndex]);
    saveTimers.current[rowIndex] = setTimeout(async () => {
      setSavingRows(prev => ({ ...prev, [rowIndex]: true }));
      try {
        await fetch(`/api/e1/${id}/matrix/${updatedRow.req_id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: updatedRow.status, notes: updatedRow.notes }),
        });
      } catch (_) {
        // Non-blocking: endpoint may not exist yet; edits are held in local state
      } finally {
        setSavingRows(prev => ({ ...prev, [rowIndex]: false }));
      }
    }, 800);
  }

  function handleStatusChange(rowIndex, status) {
    setRows(prev => {
      const next = prev.map((r, i) => i === rowIndex ? { ...r, status } : r);
      scheduleSave(rowIndex, next[rowIndex]);
      return next;
    });
  }

  function handleNotesChange(rowIndex, notes) {
    setRows(prev => {
      const next = prev.map((r, i) => i === rowIndex ? { ...r, notes } : r);
      scheduleSave(rowIndex, next[rowIndex]);
      return next;
    });
  }

  function toggleExpand(rowIndex) {
    setExpandedRows(prev => ({ ...prev, [rowIndex]: !prev[rowIndex] }));
  }

  async function handleApprove() {
    setApproving(true);
    try {
      const res = await fetch(`/api/e1/${id}/checkpoint2/approve`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail ?? `Server error ${res.status}`);
      }
      setToast({
        message: "Compliance matrix generated and approved!",
        downloadUrl: `/api/e1/${id}/download/matrix`,
      });
      setTimeout(() => router.push(`/e1/${id}/complete`), 4000);
    } catch (err) {
      setToast({ message: `Approval failed: ${err.message}`, downloadUrl: null });
      setApproving(false);
    }
  }

  // Loading
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Spinner />
          <p className="text-sm text-gray-500">Loading compliance matrix…</p>
        </div>
      </div>
    );
  }

  // 404 guard
  if (loadError === "404" || loadError?.includes("not yet generated")) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-8">
        <div className="max-w-md rounded-xl border border-yellow-200 bg-yellow-50 p-6 text-center">
          <p className="font-semibold text-yellow-800">Compliance matrix not yet generated</p>
          <p className="mt-1 text-sm text-yellow-700">Complete Checkpoint 1 first to generate the matrix.</p>
          <a href={`/e1/${id}/checkpoint1`} className="mt-4 inline-block text-sm text-blue-600 underline">← Go to Checkpoint 1</a>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-8">
        <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-semibold text-red-800">Failed to load matrix</p>
          <p className="mt-1 text-sm text-red-600">{loadError}</p>
          <a href={`/e1/${id}/checkpoint1`} className="mt-4 inline-block text-sm text-blue-600 underline">← Back to Checkpoint 1</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-32">

      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-7xl">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/" className="hover:text-gray-800">BOMATIC</a>
            <span>/</span>
            <a href={`/e1/${id}`} className="hover:text-gray-800">Opportunity {id}</a>
            <span>/</span>
            <a href={`/e1/${id}/checkpoint1`} className="hover:text-gray-800">Checkpoint 1</a>
            <span>/</span>
            <span className="font-medium text-gray-800">Checkpoint 2</span>
          </div>
          <h1 className="mt-2 text-xl font-bold text-gray-900">Checkpoint 2 — Review Compliance Matrix</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Review the auto-generated matrix, edit statuses and notes, then approve to generate the Excel output.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">

        {/* Stats bar */}
        <SectionCard title="Summary">
          <StatsBar stats={stats} />
        </SectionCard>

        {/* Compliance Matrix table */}
        <SectionCard title={`Compliance Matrix (${rows.length} rows)`}>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-gray-50">
                  {["Req #", "Requirement Text", "Classification", "Framework", "Control ID", "Control Name", "Status", "TP Section", "Notes", "Gap Type"].map(h => (
                    <th key={h} className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map((row, i) => (
                  <MatrixRow
                    key={i}
                    row={row}
                    onStatusChange={val => handleStatusChange(i, val)}
                    onNotesChange={val => handleNotesChange(i, val)}
                    saving={!!savingRows[i]}
                    expanded={!!expandedRows[i]}
                    onToggleExpand={() => toggleExpand(i)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        {/* Gap Analysis */}
        <SectionCard title="Gap Analysis">
          <GapAnalysis gaps={gaps} />
        </SectionCard>

      </div>

      {/* Sticky bottom bar */}
      <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-gray-200 bg-white px-6 py-4 shadow-lg">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <a
            href={`/e1/${id}/checkpoint1`}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            ← Back to Checkpoint 1
          </a>
          <button
            onClick={handleApprove}
            disabled={approving}
            className="flex items-center gap-2 rounded-lg bg-green-600 px-5 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {approving && <Spinner small />}
            {approving ? "Generating…" : "Approve & Generate Excel"}
          </button>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          downloadUrl={toast.downloadUrl}
          onClose={dismissToast}
        />
      )}
    </div>
  );
}
