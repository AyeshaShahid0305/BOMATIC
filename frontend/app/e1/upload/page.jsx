"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";

export default function E1UploadPage() {
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [loadingStage, setLoadingStage] = useState(null); // null | "uploading" | "analyzing"
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const router = useRouter();

  function addFiles(incoming) {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name));
      const novel = Array.from(incoming).filter(f => !existing.has(f.name));
      return [...prev, ...novel];
    });
  }

  function removeFile(name) {
    setFiles(prev => prev.filter(f => f.name !== name));
  }

  async function handleUpload() {
    setError(null);

    const form = new FormData();
    files.forEach(f => form.append("files", f));
    if (projectName.trim()) form.append("project_name", projectName.trim());

    let opportunityId;

    try {
      setLoadingStage("uploading");
      const uploadRes = await fetch("/api/v1/rfp/packages", { method: "POST", body: form });
      if (!uploadRes.ok) {
        const text = await uploadRes.text();
        throw new Error(text || `Upload failed: ${uploadRes.status}`);
      }
      const uploadData = await uploadRes.json();
      opportunityId = uploadData.opportunity_id;
    } catch (err) {
      setError(err.message);
      setLoadingStage(null);
      return;
    }

    try {
      setLoadingStage("analyzing");
      const runRes = await fetch(`/api/e1/${opportunityId}/run`, { method: "POST" });
      if (!runRes.ok) {
        const text = await runRes.text();
        throw new Error(text || `Analysis failed: ${runRes.status}`);
      }
    } catch (err) {
      setError(err.message);
      setLoadingStage(null);
      return;
    }

    router.push(`/e1/${opportunityId}/checkpoint1`);
  }

  const loading = loadingStage !== null;

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Upload RFP Documents</h1>

      <div
        onDrop={e => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
          dragging
            ? "border-blue-400 bg-blue-50"
            : "border-gray-300 bg-gray-50 hover:border-gray-400"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={e => { addFiles(e.target.files); e.target.value = ""; }}
        />
        <p className="text-sm text-gray-500">
          Drag & drop files here, or{" "}
          <span className="text-blue-600 underline">browse</span>
        </p>
        <p className="mt-1 text-xs text-gray-400">PDF, DOCX, TXT supported</p>
      </div>

      {files.length > 0 && (
        <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200">
          {files.map(f => (
            <li key={f.name} className="flex items-center gap-3 px-4 py-2">
              <span className="flex-1 truncate text-sm text-gray-700">{f.name}</span>
              <span className="shrink-0 text-xs text-gray-400">
                {(f.size / 1024).toFixed(1)} KB
              </span>
              <button
                onClick={() => removeFile(f.name)}
                className="shrink-0 text-gray-400 hover:text-red-500"
                aria-label={`Remove ${f.name}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Project name <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <input
          type="text"
          value={projectName}
          onChange={e => setProjectName(e.target.value)}
          placeholder="e.g. City Hall HVAC Upgrade"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={files.length === 0 || loading}
        className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading && (
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V0A12 12 0 000 12h4z" />
          </svg>
        )}
        {loadingStage === "uploading"
          ? "Uploading files…"
          : loadingStage === "analyzing"
          ? "Analyzing RFP…"
          : "Analyze"}
      </button>
    </div>
  );
}
