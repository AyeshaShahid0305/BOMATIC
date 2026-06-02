"use client";

import { useState } from "react";

type RevisionModalProps = {
  engineLabel: string;
  onClose: () => void;
  onSubmit: (notes: string) => void;
  submitting: boolean;
};

export default function RevisionModal({ engineLabel, onClose, onSubmit, submitting }: RevisionModalProps) {
  const [notes, setNotes] = useState("");

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
        <h3 className="mb-1 text-base font-semibold text-gray-800">Request {engineLabel} Revision</h3>
        <p className="mb-4 text-sm text-gray-500">
          Describe what needs to be corrected. After submitting, re-run the engine with updated inputs.
        </p>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={5}
          placeholder="e.g. The BoQ template used was incorrect - re-upload with the updated version."
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
            {submitting ? "Submitting" : "Submit Revision Request"}
          </button>
        </div>
      </div>
    </div>
  );
}
