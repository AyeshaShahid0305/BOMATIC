export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">BOMATIC</h1>
          <p className="text-gray-500 mt-1">Pre-Sales Engineering Assistant — Phase 0</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 font-bold text-sm">
                E1
              </div>
              <h2 className="text-lg font-semibold text-gray-800">Upload RFP Package</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Upload an RFP document package to start the 12-step E1 parsing pipeline.
              Produces a compliance matrix, requirements baseline, and risk flags report.
            </p>
            <a
              href="/e1/upload"
              className="block w-full py-2 px-4 bg-blue-600 text-white rounded-lg text-sm font-medium text-center hover:bg-blue-700"
            >
              Upload Files
            </a>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center text-green-700 font-bold text-sm">
                E2
              </div>
              <h2 className="text-lg font-semibold text-gray-800">BoM Builder</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Upload a vendor BoQ template and match it against your RFP requirements.
              Produces a priced Bill of Materials with gap analysis and SI discount applied.
            </p>
            <a
              href="/e2"
              className="block w-full py-2 px-4 bg-green-600 text-white rounded-lg text-sm font-medium text-center hover:bg-green-700"
            >
              Open BoM Builder
            </a>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center text-purple-700 font-bold text-sm">
                E3
              </div>
              <h2 className="text-lg font-semibold text-gray-800">Proposal Generator</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Generate a formatted Technical Proposal Word document from an RFP session.
              Includes AI-written narratives, pricing table, and compliance matrix.
            </p>
            <a
              href="/e3"
              className="block w-full py-2 px-4 bg-purple-600 text-white rounded-lg text-sm font-medium text-center hover:bg-purple-700"
            >
              Open Proposal Generator
            </a>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center text-purple-600 font-bold text-sm">
                #
              </div>
              <h2 className="text-lg font-semibold text-gray-800">My Opportunities</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              View all RFP packages and their pipeline status across the 6 pre-sales gates.
            </p>
            <button
              disabled
              className="w-full py-2 px-4 bg-purple-600 text-white rounded-lg text-sm font-medium opacity-40 cursor-not-allowed"
            >
              View Opportunities — coming in Phase 1
            </button>
          </div>
        </div>

        <div className="mt-8 bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Phase Roadmap</h3>
          <div className="space-y-2 text-sm">
            {[
              { phase: "Phase 0", label: "Foundation — FastAPI + DB + Next.js shell", done: true },
              { phase: "Phase 1", label: "File upload + text extraction + Step 1 classifier", done: false },
              { phase: "Phase 2", label: "E1 Steps 2–5: requirements, legal traps, Checkpoint 1", done: false },
              { phase: "Phase 3", label: "E1 Steps 6–12: compliance matrix, outputs, Checkpoint 2", done: false },
            ].map(({ phase, label, done }) => (
              <div key={phase} className="flex items-center gap-3">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${done ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}>
                  {done ? "v" : "-"}
                </span>
                <span className="font-medium text-gray-700 w-20 flex-shrink-0">{phase}</span>
                <span className="text-gray-500">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
