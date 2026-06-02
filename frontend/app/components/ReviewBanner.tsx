"use client";

import { useEffect, useState } from "react";

type ReviewResult = {
  passed: boolean;
  warnings: string[];
  errors: string[];
  checked_at: string;
};

type ReviewBannerProps = {
  opportunityId: string;
  checkpoint: "cp1" | "cp2";
  /** Called with true when errors=[] (approve button should enable), false otherwise */
  onReady: (canApprove: boolean) => void;
};

export default function ReviewBanner({ opportunityId, checkpoint, onReady }: ReviewBannerProps) {
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);

  async function fetchReview() {
    setLoading(true);
    try {
      const res = await fetch(
        `/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}`
      );
      if (res.status === 404) {
        // Reviewer hasn't run yet - treat as passed with no issues.
        onReady(true);
        return;
      }
      if (!res.ok) throw new Error(`${res.status}`);
      const data: ReviewResult = await res.json();
      setReview(data);
      onReady(data.errors.length === 0);
    } catch {
      // On fetch error, don't block the engineer.
      onReady(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleRerun() {
    setRerunning(true);
    try {
      const res = await fetch(
        `/api/e1/${encodeURIComponent(opportunityId)}/review/${checkpoint}/rerun`,
        { method: "POST" }
      );
      if (res.ok) {
        const data: ReviewResult = await res.json();
        setReview(data);
        onReady(data.errors.length === 0);
      }
    } catch {
      // Non-blocking.
    } finally {
      setRerunning(false);
    }
  }

  useEffect(() => {
    fetchReview();
  }, [opportunityId, checkpoint]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-5 py-4 text-sm text-gray-400 shadow-sm">
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
        </svg>
        Running automated review
      </div>
    );
  }

  if (!review) return null;

  const hasErrors = review.errors.length > 0;
  const hasWarnings = review.warnings.length > 0;

  if (!hasErrors && !hasWarnings) {
    return (
      <div className="flex items-center justify-between rounded-xl border border-green-200 bg-green-50 px-5 py-4 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-500 text-white text-xs font-bold" />
          <span className="text-sm font-medium text-green-800">Automated review passed - no issues found.</span>
        </div>
        <button
          onClick={handleRerun}
          disabled={rerunning}
          className="text-xs text-green-600 underline hover:text-green-800 disabled:opacity-50"
        >
          {rerunning ? "Re-running" : "Re-run"}
        </button>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border shadow-sm ${hasErrors ? "border-red-200 bg-red-50" : "border-yellow-200 bg-yellow-50"}`}>
      <div className="flex items-center justify-between px-5 py-4">
        <div className="flex items-center gap-3">
          <span className={`flex h-6 w-6 items-center justify-center rounded-full text-white text-xs font-bold ${hasErrors ? "bg-red-500" : "bg-yellow-500"}`}>
            {hasErrors ? "!" : ""}
          </span>
          <span className={`text-sm font-semibold ${hasErrors ? "text-red-800" : "text-yellow-800"}`}>
            {hasErrors
              ? `Automated review found ${review.errors.length} issue(s) that must be resolved.`
              : `Automated review passed with ${review.warnings.length} warning(s).`}
          </span>
        </div>
        <button
          onClick={handleRerun}
          disabled={rerunning}
          className={`text-xs underline disabled:opacity-50 ${hasErrors ? "text-red-600 hover:text-red-800" : "text-yellow-600 hover:text-yellow-800"}`}
        >
          {rerunning ? "Re-running" : "Re-run"}
        </button>
      </div>

      {hasErrors && (
        <div className="space-y-2 border-t border-red-200 px-5 pb-4 pt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-red-600">Must Fix</p>
          <ul className="space-y-1.5">
            {review.errors.map((e, i) => (
              <li key={i} className="flex gap-2 text-sm text-red-700">
                <span className="mt-0.5 shrink-0" />
                <span>{e}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasWarnings && (
        <div className={`space-y-2 border-t px-5 pb-4 pt-3 ${hasErrors ? "border-red-200" : "border-yellow-200"}`}>
          <p className={`text-xs font-semibold uppercase tracking-wide ${hasErrors ? "text-red-500" : "text-yellow-600"}`}>
            Warnings
          </p>
          <ul className="space-y-1.5">
            {review.warnings.map((w, i) => (
              <li key={i} className={`flex gap-2 text-sm ${hasErrors ? "text-red-600" : "text-yellow-700"}`}>
                <span className="mt-0.5 shrink-0" />
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasErrors && (
        <div className="border-t border-red-200 px-5 py-3">
          <p className="text-xs text-red-500">
            Fix the issues above, then click Re-run to clear this block. The Approve button is
            disabled until all errors are resolved.
          </p>
        </div>
      )}
    </div>
  );
}
