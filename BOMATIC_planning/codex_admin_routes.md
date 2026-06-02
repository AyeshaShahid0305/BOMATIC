# Codex Task: Admin Routes + Admin Dashboard Page

## Context

BOMATIC has JWT authentication with two roles: "engineer" and "admin". The
`get_current_admin` dependency in `backend/app/api/deps.py` already exists and
returns 403 for non-admins. No admin routes or admin UI exist yet.

This task adds:
1. `backend/app/api/admin_routes.py` — four admin endpoints
2. Register the admin router in `backend/app/main.py`
3. `frontend/app/admin/page.tsx` — admin dashboard page (opportunities + users)

---

## Step 1 — Read these files first

1. `backend/app/api/deps.py` — get_current_user, get_current_admin
2. `backend/app/api/auth_routes.py` — UserResponse schema to reuse
3. `backend/app/models/user.py`
4. `backend/app/models/opportunity.py`
5. `backend/app/models/pipeline_state.py`
6. `backend/app/routers/rfp.py` — list_opportunities pattern to follow
7. `backend/app/main.py` — where to register the new router
8. `frontend/app/opportunities/page.tsx` — card layout pattern to follow

---

## Step 2 — Create `backend/app/api/admin_routes.py`

```python
"""
Admin routes — require role='admin'.

GET  /api/admin/opportunities  — all opportunities across all engineers
GET  /api/admin/users          — all registered users
POST /api/admin/users/{user_id}/deactivate  — deactivate a user account
POST /api/admin/users/{user_id}/activate    — reactivate a user account
GET  /api/admin/stats          — platform-wide counts
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db import get_db
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Opportunities — all, regardless of owner
# ---------------------------------------------------------------------------

@router.get("/opportunities")
def admin_list_opportunities(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Return all opportunities across all engineers with pipeline progress."""
    rows = (
        db.query(Opportunity, PipelineState)
        .join(PipelineState, PipelineState.opportunity_id == Opportunity.id)
        .order_by(Opportunity.created_at.desc())
        .all()
    )

    return [
        {
            "opportunity_id": opp.opportunity_id,
            "project_name": opp.project_name,
            "client_name": opp.client_name,
            "mode": opp.mode,
            "status": opp.status,
            "current_step": pipeline.current_step,
            "created_at": opp.created_at.isoformat(),
            "updated_at": opp.updated_at.isoformat(),
            "owner_user_id": str(opp.user_id) if opp.user_id else None,
            "engines_completed": list((pipeline.step_outputs or {}).keys()),
        }
        for opp, pipeline in rows
    ]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users")
def admin_list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Return all registered users."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("/users/{user_id}/deactivate")
def admin_deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Deactivate a user account (they can no longer log in)."""
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    db.commit()
    return {"id": user_id, "is_active": False, "message": f"{user.email} deactivated."}


@router.post("/users/{user_id}/activate")
def admin_activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Reactivate a deactivated user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    db.commit()
    return {"id": user_id, "is_active": True, "message": f"{user.email} activated."}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Platform-wide statistics."""
    total_opps = db.query(Opportunity).count()
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712

    # Count by status
    from sqlalchemy import func
    status_counts_raw = (
        db.query(Opportunity.status, func.count(Opportunity.id))
        .group_by(Opportunity.status)
        .all()
    )
    status_counts = {status: count for status, count in status_counts_raw}

    completed = sum(
        v for k, v in status_counts.items()
        if k == "complete" or k.endswith("_complete") or k.endswith("_approved")
    )

    return {
        "total_opportunities": total_opps,
        "completed_opportunities": completed,
        "in_progress_opportunities": total_opps - completed,
        "total_users": total_users,
        "active_users": active_users,
        "status_breakdown": status_counts,
    }
```

---

## Step 3 — Register in `backend/app/main.py`

Add the admin router import after the existing router imports:
```python
from app.api.admin_routes import router as admin_router
```

Add the exclude path for the admin endpoints — they use JWT (not excluded from API key),
so no change to `_EXCLUDED_PATHS` is needed.

Register the router after the other routers:
```python
app.include_router(admin_router, prefix="/api")
```

---

## Step 4 — Create `frontend/app/admin/page.tsx`

```tsx
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
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }).format(new Date(s));
  } catch { return s; }
}

function StatusBadge({ status }: { status: string }) {
  const color = status === "complete" ? "bg-green-100 text-green-700"
    : status.endsWith("_approved") ? "bg-blue-100 text-blue-700"
    : status.endsWith("_complete") ? "bg-green-100 text-green-600"
    : status === "uploaded" ? "bg-gray-100 text-gray-600"
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
    // Verify admin access via /auth/me
    fetch("/api/auth/me")
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(me => {
        if (me.role !== "admin") {
          router.replace("/opportunities");
          return;
        }
        // Load all admin data in parallel
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
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: !currentlyActive } : u));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50">
      <p className="text-sm text-gray-400">Loading admin dashboard…</p>
    </main>
  );

  if (error) return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-8">
      <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="font-semibold text-red-800">{error}</p>
        <a href="/opportunities" className="mt-4 inline-block text-sm text-blue-600 underline">← Back to Opportunities</a>
      </div>
    </main>
  );

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-8">
      <div className="mx-auto max-w-6xl space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <a href="/opportunities" className="hover:text-gray-800">BOMATIC</a>
              <span>/</span>
              <span className="font-medium text-gray-800">Admin</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold text-gray-900">Admin Dashboard</h1>
          </div>
          <a href="/opportunities"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            ← My Opportunities
          </a>
        </div>

        {/* Stats */}
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

        {/* Tabs */}
        <div className="flex gap-1 rounded-lg border border-gray-200 bg-white p-1 shadow-sm w-fit">
          {(["opportunities", "users"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition-colors ${
                tab === t ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {t} {t === "opportunities" ? `(${opportunities.length})` : `(${users.length})`}
            </button>
          ))}
        </div>

        {/* Opportunities tab */}
        {tab === "opportunities" && (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Opportunity ID", "Project", "Client", "Mode", "Status", "Step", "Owner", "Created"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {opportunities.map(opp => (
                  <tr key={opp.opportunity_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{opp.opportunity_id}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{opp.project_name || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{opp.client_name || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium uppercase ${
                        opp.mode === "rfi" ? "bg-orange-100 text-orange-700" : "bg-blue-100 text-blue-700"
                      }`}>{opp.mode}</span>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={opp.status} /></td>
                    <td className="px-4 py-3 text-gray-600">{opp.current_step}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">{opp.owner_user_id?.slice(0, 8) ?? "anon"}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{formatDate(opp.created_at)}</td>
                  </tr>
                ))}
                {opportunities.length === 0 && (
                  <tr><td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-400">No opportunities yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Users tab */}
        {tab === "users" && (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Email", "Name", "Role", "Status", "Created", "Actions"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-800">{user.email}</td>
                    <td className="px-4 py-3 text-gray-600">{user.full_name || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                        user.role === "admin" ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-600"
                      }`}>{user.role}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        user.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
                      }`}>{user.is_active ? "Active" : "Inactive"}</span>
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
                        {actionLoading === user.id ? "…" : user.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">No users found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

      </div>
    </main>
  );
}
```

---

## Step 5 — Validation steps

### 5A. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/admin_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/main.py
```
Expected: no output.

### 5B. Import check
```
backend\.venv\Scripts\python.exe -c "
from app.api.admin_routes import router
from app.api.deps import get_current_admin
print('admin imports OK')
print('routes:', [r.path for r in router.routes])
"
```
Expected: `admin imports OK` then a list of 5 route paths.

### 5C. Route smoke test
```
backend\.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, 'backend')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
headers = {'X-API-Key': 'bomatic-dev-key'}

# Without JWT — should return 401 (not 403 or 500)
for path in ['/api/admin/opportunities', '/api/admin/users', '/api/admin/stats']:
    r = client.get(path, headers=headers)
    assert r.status_code == 401, f'{path}: expected 401 got {r.status_code}'
    print(f'{path}: 401 PASS')

print('All admin route checks passed.')
"
```
Expected: 3 `401 PASS` lines.

### 5D. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 5E. Frontend build
```
cd frontend && npm run build
```
Expected: zero errors. `/admin` appears in the build output as a new page.

---

## Step 6 — Summary of files changed

| Action   | File path                              |
|----------|----------------------------------------|
| Created  | `backend/app/api/admin_routes.py`      |
| Modified | `backend/app/main.py`                  |
| Created  | `frontend/app/admin/page.tsx`          |

No DB migration. No new dependencies.

---

## Step 7 — Git commit message

```
feat: add admin routes and admin dashboard page

backend/app/api/admin_routes.py:
- GET /api/admin/opportunities — all opportunities across all engineers
- GET /api/admin/users — all registered users with active status
- POST /api/admin/users/{id}/deactivate — deactivate user (403 for self)
- POST /api/admin/users/{id}/activate — reactivate user
- GET /api/admin/stats — total/completed/in-progress counts, status breakdown
  All routes require role='admin' via get_current_admin dependency (403 for engineers)

main.py: register admin_router under /api prefix

frontend/app/admin/page.tsx:
- Checks /auth/me on load; redirects non-admins to /opportunities
- Stats row: total opps, completed, in-progress, total users, active users
- Opportunities tab: full table with status badge, mode badge, owner ID, step
- Users tab: email, name, role, active status, deactivate/activate toggle button
```
