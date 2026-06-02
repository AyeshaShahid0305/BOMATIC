"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Opportunity = {
  opportunity_id: string;
  project_name: string | null;
  client_name: string | null;
  mode: string;
  status: string;
  current_step: number;
  created_at: string;
  owner_user_id: string | null;
};

type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

type Stats = {
  total_opportunities: number;
  completed_opportunities: number;
  in_progress_opportunities: number;
  total_users: number;
  active_users: number;
  status_breakdown: Record<string, number>;
};

function formatDate(s: string) {
  try {
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(s));
  } catch {
    return s;
  }
}

function StatusBadge({ status }: { status: string }) {
  const color = status === "complete"
    ? "bg-green-100 text-green-700"
    : status.endsWith("_approved")
      ? "bg-blue-100 text-blue-700"
      : status.endsWith("_complete")
        ? "bg-green-100 text-green-600"
        : status === "uploaded"
          ? "bg-gray-100 text-gray-600"
          : "bg-yellow-100 text-yellow-700";

  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${color}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"opportunities" | "users">("opportunities");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/auth/me")
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(me => {
        if (me.role !== "admin") {
          router.replace("/opportunities");
          return null;
        }

        return Promise.all([
          fetch("/api/admin/opportunities").then(r => r.json()),
          fetch("/api/admin/users").then(r => r.json()),
          fetch("/api/admin/stats").then(r => r.json()),
        ]);
      })
      .then(results => {
        if (!results) return;
        setOpportunities(results[0]);
        setUsers(results[1]);
        setStats(results[2]);
      })
      .catch(() => setError("Failed to load admin data. You may not have admin access."))
      .finally(() => setLoading(false));
  }, [router]);

  async function toggleUser(userId: string, currentlyActive: boolean) {
    setActionLoading(userId);
    const action = currentlyActive ? "deactivate" : "activate";

    try {
      const res = await fetch(`/api/admin/users/${userId}/${action}`, { method: "POST" });
      if (!res.ok) {
        const b = await res.json().catch(() => null);
        throw new Error(b?.detail ?? `Failed to ${action} user`);
      }

      setUsers(prev => prev.map(u => (
        u.id === userId ? { ...u, is_active: !currentlyActive } : u
      )));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-400">Loading admin dashboard</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 p-8">
        <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-semibold text-red-800">{error}</p>
          <a href="/opportunities" className="mt-4 inline-block text-sm text-blue-600 underline">
            Back to Opportunities
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <a href="/opportunities" className="hover:text-gray-800">BOMATIC</a>
              <span>/</span>
              <span className="font-medium text-gray-800">Admin</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold text-gray-900">Admin Dashboard</h1>
          </div>
          <a
            href="/opportunities"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            My Opportunities
          </a>
        </div>

        {stats && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            {[
              { label: "Total Opportunities", value: stats.total_opportunities, color: "text-gray-900" },
              { label: "Completed", value: stats.completed_opportunities, color: "text-green-700" },
              { label: "In Progress", value: stats.in_progress_opportunities, color: "text-blue-700" },
              { label: "Total Users", value: stats.total_users, color: "text-gray-900" },
              { label: "Active Users", value: stats.active_users, color: "text-gray-900" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</p>
                <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
              </div>
            ))}
          </div>
        )}

        <div className="flex w-fit gap-1 rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
          {(["opportunities", "users"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition-colors ${
                tab === t ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {t} {t === "opportunities" ? `(${opportunities.length})` : `(${users.length})`}
            </button>
          ))}
        </div>

        {tab === "opportunities" && (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Opportunity ID", "Project", "Client", "Mode", "Status", "Step", "Owner", "Created"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {opportunities.map(opp => (
                  <tr key={opp.opportunity_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{opp.opportunity_id}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{opp.project_name || ""}</td>
                    <td className="px-4 py-3 text-gray-600">{opp.client_name || ""}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium uppercase ${
                        opp.mode === "rfi" ? "bg-orange-100 text-orange-700" : "bg-blue-100 text-blue-700"
                      }`}>
                        {opp.mode}
                      </span>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={opp.status} /></td>
                    <td className="px-4 py-3 text-gray-600">{opp.current_step}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">
                      {opp.owner_user_id?.slice(0, 8) ?? "anon"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">{formatDate(opp.created_at)}</td>
                  </tr>
                ))}
                {opportunities.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-400">
                      No opportunities yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {tab === "users" && (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Email", "Name", "Role", "Status", "Created", "Actions"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-800">{user.email}</td>
                    <td className="px-4 py-3 text-gray-600">{user.full_name || ""}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                        user.role === "admin" ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-600"
                      }`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        user.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
                      }`}>
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">{formatDate(user.created_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => toggleUser(user.id, user.is_active)}
                        disabled={actionLoading === user.id}
                        className={`rounded px-2.5 py-1 text-xs font-medium disabled:opacity-50 ${
                          user.is_active
                            ? "bg-red-50 text-red-600 hover:bg-red-100"
                            : "bg-green-50 text-green-700 hover:bg-green-100"
                        }`}
                      >
                        {actionLoading === user.id ? "" : user.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
