# Codex Task: Feature 6 — Authentication + Per-Engineer Sessions

## Context

BOMATIC is a FastAPI + Next.js + PostgreSQL pre-sales platform. Currently, all API
requests are authenticated only by a shared static `X-API-Key` header (value
`bomatic-dev-key`), injected by `frontend/middleware.ts` for every request. There is
no user identity — all engineers share one anonymous state and can see each other's
opportunities.

This task adds full JWT-based authentication. Engineers register and log in with email
and password. JWTs are stored in httpOnly cookies. The Next.js middleware reads the
cookie and forwards the token to the backend. Opportunities are owned by the engineer
who created them. Existing opportunities (no owner) remain accessible only to admins.

Do not remove the `X-API-Key` check — keep it as-is. The JWT layer is additive: routes
that need user ownership use a new `get_current_user` dependency; other routes are
unchanged.

---

## Step 1 — Read these files first (in this order)

Read every file completely before writing any code.

1. `backend/requirements.txt`
2. `backend/app/config.py`
3. `backend/app/db.py`
4. `backend/app/models/__init__.py`
5. `backend/app/models/opportunity.py`
6. `backend/app/main.py`
7. `backend/app/routers/rfp.py`
8. `backend/app/api/pipeline_routes.py`
9. `backend/alembic/env.py`
10. `backend/alembic/versions/f6f2a0d6e3b1_add_mode_to_opportunities.py`
11. `frontend/middleware.ts`
12. `frontend/app/layout.tsx`
13. `frontend/next.config.mjs`

---

## Step 2 — Backend changes

### 2A. Add dependencies to `backend/requirements.txt`

Append these two lines (do not remove or change any existing lines):

```
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
```

Install them in the project venv before running any further steps:
```
backend\.venv\Scripts\pip.exe install passlib[bcrypt]==1.7.4 "python-jose[cryptography]==3.3.0"
```

---

### 2B. Update `backend/app/config.py`

Add three new fields to the `Settings` class after the existing `bomatic_api_key` field:

```python
jwt_secret_key: str = "change-me-in-production"
jwt_algorithm: str = "HS256"
jwt_expire_minutes: int = 480  # 8 hours
```

No other changes to this file.

---

### 2C. Create `backend/app/models/user.py`

Create this file with exactly this content:

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="engineer")
    # role values: "engineer" | "admin"
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

---

### 2D. Update `backend/app/models/__init__.py`

Add the User import so Alembic picks it up for autogenerate. Replace the entire file with:

```python
from app.models.opportunity import Opportunity
from app.models.document import Document
from app.models.pipeline_state import PipelineState
from app.models.user import User

__all__ = ["Opportunity", "Document", "PipelineState", "User"]
```

---

### 2E. Create Alembic migration for the `users` table

Run this command from the `backend/` directory to generate the migration:

```
backend\.venv\Scripts\alembic.exe revision --autogenerate -m "add_users_table"
```

Open the generated file in `backend/alembic/versions/`. Verify the `upgrade()` function
creates a `users` table with columns: `id` (UUID PK), `email` (VARCHAR 255, unique,
not null), `hashed_password` (VARCHAR 255, not null), `full_name` (VARCHAR 255, not null,
server_default ''), `role` (VARCHAR 20, not null, server_default 'engineer'),
`is_active` (BOOLEAN, not null, server_default true), `created_at` (TIMESTAMPTZ).

If autogenerate produces the correct table, apply it:
```
backend\.venv\Scripts\alembic.exe upgrade head
```

If autogenerate produces an empty migration (no `op.create_table`), write the upgrade
manually:

```python
def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("role", sa.String(20), nullable=False, server_default="engineer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

Then apply:
```
backend\.venv\Scripts\alembic.exe upgrade head
```

---

### 2F. Create `backend/app/api/deps.py`

Create this file with exactly this content:

```python
"""
Shared FastAPI dependencies.

get_current_user: validates the JWT from the Authorization header and returns
the authenticated User. Use as a route dependency when a route needs to know
which engineer is making the request.

Usage:
    from app.api.deps import get_current_user
    from app.models.user import User

    @router.get("/some-route")
    def some_route(current_user: User = Depends(get_current_user)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate the JWT from the Authorization: Bearer <token> header.
    Returns the authenticated User or raises HTTP 401.
    """
    settings = get_settings()

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token.",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require role='admin'. Use for admin-only routes."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user
```

---

### 2G. Create `backend/app/api/auth_routes.py`

Create this file with exactly this content:

```python
"""
Authentication routes.

POST /api/auth/register  — create a new engineer account, return JWT
POST /api/auth/login     — verify credentials, return JWT
GET  /api/auth/me        — return current user info (requires valid JWT)
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Pydantic schemas (request / response bodies)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def _create_token(user_id: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new engineer account and return a JWT."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    user = User(
        email=body.email,
        hashed_password=_hash_password(body.password),
        full_name=body.full_name,
        role="engineer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=_create_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Verify credentials and return a JWT."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive.")

    return TokenResponse(access_token=_create_token(str(user.id)))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
    )
```

---

### 2H. Update `backend/app/main.py`

Make two changes:

**Change 1** — Add the auth router import after the existing router imports:
```python
from app.api.auth_routes import router as auth_router
```

**Change 2** — Add `/api/auth/login` and `/api/auth/register` to `_EXCLUDED_PATHS`
so they are reachable without an API key (they use password auth instead):
```python
_EXCLUDED_PATHS = {"/docs", "/health", "/openapi.json", "/redoc", "/api/auth/login", "/api/auth/register"}
```

**Change 3** — Register the auth router after the other routers:
```python
app.include_router(auth_router, prefix="/api")
```

No other changes to `main.py`.

---

### 2I. Update `backend/app/routers/rfp.py`

Make these two targeted changes only. Do not touch any other function.

**Change 1 — `upload_rfp_package`**: Accept an optional `Authorization` header and wire
`owner_id` to the opportunity when a valid user is identified.

Add this import at the top of `rfp.py` (with the other imports):
```python
from fastapi import Header
from jose import JWTError, jwt
```

Modify the `upload_rfp_package` function signature to accept an optional Authorization
header:
```python
async def upload_rfp_package(
    files: list[UploadFile] = File(...),
    opportunity_id: Optional[str] = Form(None),
    client_name: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
```

Inside the function, before `db.add(opportunity)`, add this block to resolve the
owner_id from the JWT if present:

```python
    # Resolve owner from JWT if provided
    owner_id: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            owner_id = payload.get("sub")
        except JWTError:
            pass  # Invalid token — treat as anonymous upload

    opportunity = Opportunity(
        opportunity_id=opp_id_str,
        client_name=client_name,
        project_name=project_name,
        status="uploaded",
        user_id=owner_id,  # None for anonymous/legacy uploads
    )
```

**Change 2 — `list_opportunities`**: Filter by `user_id` when a JWT is present.
Same pattern — add `authorization: Optional[str] = Header(default=None)` to the
function signature, then resolve `owner_id` from the token. If `owner_id` is resolved,
add `.filter(Opportunity.user_id == owner_id)` to the query. If `owner_id` is None
(anonymous or no token), return all opportunities (legacy behaviour — keeps existing
sessions visible).

Full replacement for `list_opportunities`:

```python
@router.get("/opportunities")
def list_opportunities(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """Return opportunities. Filters by owner when a valid JWT is present."""
    owner_id: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            owner_id = payload.get("sub")
        except JWTError:
            pass

    query = (
        db.query(Opportunity, PipelineState)
        .join(PipelineState, PipelineState.opportunity_id == Opportunity.id)
        .order_by(Opportunity.created_at.desc())
    )

    if owner_id:
        query = query.filter(Opportunity.user_id == owner_id)

    rows = query.all()

    return [
        {
            "opportunity_id": opportunity.opportunity_id,
            "project_name": opportunity.project_name,
            "client_name": opportunity.client_name,
            "status": opportunity.status,
            "current_step": pipeline.current_step,
            "created_at": opportunity.created_at.isoformat(),
            "engines_completed": list((pipeline.step_outputs or {}).keys()),
        }
        for opportunity, pipeline in rows
    ]
```

---

## Step 3 — Frontend changes

### 3A. Create `frontend/app/login/page.tsx`

Create a clean login page. It posts to a Next.js API route (not directly to the
backend) so the cookie can be set server-side.

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `Login failed (${res.status})`);
      }

      router.push("/opportunities");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">BOMATIC</h1>
          <p className="mt-1 text-sm text-gray-500">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="you@company.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {error && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400">
          No account? Ask your BOMATIC admin to create one.
        </p>
      </div>
    </main>
  );
}
```

---

### 3B. Create `frontend/app/api/auth/login/route.ts`

This Next.js Route Handler calls the backend and sets the JWT in a secure httpOnly cookie.

```ts
import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const backendRes = await fetch(`${BACKEND}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await backendRes.json();

  if (!backendRes.ok) {
    return NextResponse.json(data, { status: backendRes.status });
  }

  const token: string = data.access_token;

  const response = NextResponse.json({ ok: true }, { status: 200 });
  response.cookies.set("bomatic_token", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 8, // 8 hours — matches jwt_expire_minutes
  });

  return response;
}
```

---

### 3C. Create `frontend/app/api/auth/logout/route.ts`

```ts
import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set("bomatic_token", "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
  });
  return response;
}
```

---

### 3D. Replace `frontend/middleware.ts`

Replace the entire file with this content:

```ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/api/auth/login", "/api/auth/logout"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always allow public paths through without any modification
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get("bomatic_token")?.value;

  // Unauthenticated: redirect browser requests to /login
  // Pass API requests through with 401 (they handle errors themselves)
  if (!token) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.next();
    }
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated: inject both the static API key and the JWT
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("X-API-Key", "bomatic-dev-key");
  requestHeaders.set("Authorization", `Bearer ${token}`);

  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|fonts).*)"],
};
```

---

### 3E. Add a logout button to `frontend/app/layout.tsx`

Replace the `<body>` contents of `layout.tsx` to include a minimal top nav with a
logout button. Keep all existing imports and metadata unchanged. Only change the
`return` statement of `RootLayout`:

```tsx
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <nav className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
          <a href="/opportunities" className="text-sm font-semibold text-gray-800 hover:text-blue-600">
            BOMATIC
          </a>
          <form action="/api/auth/logout" method="POST">
            <button
              type="submit"
              className="text-xs text-gray-400 hover:text-gray-700"
            >
              Sign out
            </button>
          </form>
        </nav>
        {children}
      </body>
    </html>
  );
}
```

Note: the logout form uses a native HTML POST so it works without JavaScript. After
posting to `/api/auth/logout`, the cookie is cleared and the user lands on the login
redirect.

---

## Step 4 — Validation steps

Run each check in order. Fix any failure before the next.

### 4A. Backend syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/models/user.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/deps.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/auth_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/main.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/routers/rfp.py
```
All must exit with no output (no errors).

### 4B. Migration check
```
backend\.venv\Scripts\alembic.exe -c backend/alembic.ini current
```
Expected: shows `f6f2a0d6e3b1 (head)` replaced by the new users migration as head.

### 4C. Backend import check
```
backend\.venv\Scripts\python.exe -c "
from app.api.auth_routes import router
from app.api.deps import get_current_user, get_current_admin
from app.models.user import User
print('all imports OK')
"
```
Expected output: `all imports OK`

### 4D. TypeScript check
```
cd frontend && npx tsc --noEmit
```
Expected: zero errors.

### 4E. Start the backend and test auth endpoints

Assume backend running on port 8000 with `BOMATIC_API_KEY=bomatic-dev-key`.

**Register a new engineer:**
```
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"engineer@test.com\", \"password\": \"testpass1\", \"full_name\": \"Test Engineer\"}" \
  | python -m json.tool
```
Expected: `{"access_token": "<jwt>", "token_type": "bearer"}`

**Login:**
```
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"engineer@test.com\", \"password\": \"testpass1\"}" \
  | python -m json.tool
```
Expected: same shape. Save the token as `TOKEN` for the next tests.

**Get current user (replace `<TOKEN>` with the actual token):**
```
curl -s http://localhost:8000/api/auth/me \
  -H "X-API-Key: bomatic-dev-key" \
  -H "Authorization: Bearer <TOKEN>" \
  | python -m json.tool
```
Expected: `{"id": "...", "email": "engineer@test.com", "full_name": "Test Engineer", "role": "engineer"}`

**Wrong password returns 401:**
```
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"engineer@test.com\", \"password\": \"wrong\"}"
```
Expected: `401`

**Duplicate registration returns 409:**
```
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"engineer@test.com\", \"password\": \"testpass1\", \"full_name\": \"Dup\"}"
```
Expected: `409`

**Opportunities filtered by owner: upload with token then list — only yours returned:**
```
curl -s -X POST http://localhost:8000/api/v1/rfp/packages \
  -H "X-API-Key: bomatic-dev-key" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "files=@some_file.pdf" \
  | python -m json.tool
# Note the opportunity_id in the response, e.g. OPP-XXXXXXXX

curl -s http://localhost:8000/api/v1/opportunities \
  -H "X-API-Key: bomatic-dev-key" \
  -H "Authorization: Bearer <TOKEN>" \
  | python -m json.tool
```
Expected: response list contains the opportunity just uploaded, with user_id set.

### 4F. Frontend build check
```
cd frontend && npm run build
```
Expected: zero errors. New pages `app/login`, `app/api/auth/login`, `app/api/auth/logout`
appear in the build output.

### 4G. Verify middleware protects routes
Start the Next.js dev server (`npm run dev`). In a browser with no cookie set, navigate
to `http://localhost:3000/opportunities`. You should be redirected to `/login`.

---

## Step 5 — Summary of files changed

| Action   | File path                                        |
|----------|--------------------------------------------------|
| Modified | `backend/requirements.txt`                       |
| Modified | `backend/app/config.py`                          |
| Created  | `backend/app/models/user.py`                     |
| Modified | `backend/app/models/__init__.py`                 |
| Created  | `backend/alembic/versions/<rev>_add_users_table.py` |
| Created  | `backend/app/api/deps.py`                        |
| Created  | `backend/app/api/auth_routes.py`                 |
| Modified | `backend/app/main.py`                            |
| Modified | `backend/app/routers/rfp.py`                     |
| Created  | `frontend/app/login/page.tsx`                    |
| Created  | `frontend/app/api/auth/login/route.ts`           |
| Created  | `frontend/app/api/auth/logout/route.ts`          |
| Modified | `frontend/middleware.ts`                         |
| Modified | `frontend/app/layout.tsx`                        |

No other files should be modified.

---

## Step 6 — Git commit message

```
feat: add JWT authentication and per-engineer opportunity ownership

Backend:
- User model (id, email, hashed_password, full_name, role, is_active)
- Alembic migration: add_users_table
- app/api/deps.py: get_current_user / get_current_admin JWT dependencies
- app/api/auth_routes.py: POST /api/auth/register, /login, GET /api/auth/me
- main.py: register auth router; exclude /api/auth/login and /register from API key check
- rfp.py: upload_rfp_package sets owner_id from JWT if present;
  list_opportunities filters by owner_id when JWT is present

Frontend:
- app/login/page.tsx: email/password login form
- app/api/auth/login/route.ts: sets httpOnly bomatic_token cookie
- app/api/auth/logout/route.ts: clears cookie
- middleware.ts: redirects unauthenticated browser requests to /login;
  injects X-API-Key + Authorization header for authenticated requests
- layout.tsx: top nav with Sign out button

Existing anonymous sessions remain accessible when no JWT is present.
passlib[bcrypt]==1.7.4 and python-jose[cryptography]==3.3.0 added to requirements.
```
