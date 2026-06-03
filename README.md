# BOMATIC

**Multi-vendor pre-sales deliverable generation platform for Systems Integrators.**

BOMATIC automates the creation of Bills of Materials, Compliance Matrices, Technical Proposals, RFI Questionnaires, and HLD/LLD Design Documents from RFP and RFI packages.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.13) |
| Frontend | Next.js 16 (TypeScript) |
| Database | PostgreSQL 17 |
| AI | Anthropic Claude (claude-sonnet-4-6) |

---

## Engines

| Engine | Mode | Input | Output |
|--------|------|-------|--------|
| E1 — RFP Parser | RFP | RFP document package | Compliance matrix XLSX, requirements DOCX |
| E2 — BoM Builder | RFP / RFI | BoQ template + E1/E5 data | BoM workbook XLSX, distributor export XLSX |
| E3 — Proposal Generator | RFP / RFI | E1 + E2 data | Technical proposal DOCX, submission PDF |
| E4 — Discovery Engine | RFI | Project details | RFI questionnaire XLSX |
| E5 — Design Engine | RFI | E4 requirements | HLD/LLD design document DOCX |

---

## Prerequisites

- Python 3.13+
- Node.js 20+
- PostgreSQL 17 (running on port 9876)
- Anthropic API key (for AI steps in E1, E2, E3, E5)

---

## Setup

### 1. Clone and configure

```bash
git clone <repo-url>
cd BOMATIC
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

Create `backend/.env`:
```
DATABASE_URL=postgresql+psycopg://bomatic:bomatic@localhost:9876/bomatic
ANTHROPIC_API_KEY=your-anthropic-api-key
UPLOAD_DIR=storage
BOMATIC_API_KEY=bomatic-dev-key
JWT_SECRET_KEY=change-me-in-production
```

Run migrations:
```bash
alembic upgrade head
```

Start the backend:
```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## Creating your first account

The registration endpoint is available via the backend API:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bomatic-dev-key" \
  -d '{"email": "you@company.com", "password": "yourpassword", "full_name": "Your Name"}'
```

Then log in at `http://localhost:3000/login`.

To make yourself an admin:
```sql
UPDATE users SET role = 'admin' WHERE email = 'you@company.com';
```

---

## RFP Mode workflow

```
Upload RFP → E1 (Parser) → E2 (BoM Builder) → E3 (Proposal Generator)
```

1. Go to `/e1/upload` → upload RFP documents
2. Complete Checkpoint 1 (review requirements) and Checkpoint 2 (review compliance matrix)
3. Go to `/e2?session_id=OPP-XXXX` → upload BoQ template, configure pricing
4. Go to `/e3?session_id=OPP-XXXX` → generate technical proposal
5. Download all outputs from the engine review pages

## RFI Mode workflow

```
E4 (Discovery) → E5 (Design) → E2 (BoM Builder) → E3 (Proposal Generator)
```

1. Go to `/e4` → generate RFI questionnaire
2. After client response, go to `/e5?session_id=OPP-XXXX` → generate HLD/LLD
3. Continue with E2 and E3 as above

---

## Key features

- **Automated compliance matrix** — maps RFP requirements to NCA ECC2, SAMA CSF, ISO 27001 controls
- **Cost stack CS-001→CS-009** — currency conversion, vendor discount, overhead, selling price, VAT
- **EoX checking** — flags end-of-life/end-of-sale SKUs in BoM
- **100-SKU catalog** — Cisco, Fortinet, Aruba, Palo Alto, Juniper
- **Automated reviewer** — Sonnet quality gate before each checkpoint
- **Revision loops** — up to 3 revisions per checkpoint with engineer notes
- **JWT authentication** — per-engineer opportunity ownership
- **Admin dashboard** — cross-engineer visibility at `/admin`
- **PDF generation** — LibreOffice headless conversion (requires LibreOffice installed)

---

## API documentation

Swagger UI available at `http://localhost:8000/docs` when the backend is running.

---

## Project structure

```
BOMATIC/
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers (e1-e5, auth, admin, pipeline)
│   │   ├── engines/      # E1-E5 processing engines
│   │   │   ├── e1/       # RFP parser steps 1-13
│   │   │   ├── e2/       # BoM engine + cost stack
│   │   │   ├── e3/       # Proposal generator
│   │   │   ├── e4/       # RFI discovery engine
│   │   │   └── e5/       # HLD/LLD design engine
│   │   ├── models/       # SQLAlchemy models
│   │   ├── routers/      # Legacy RFP + opportunities router
│   │   └── data/         # Compliance framework JSON files
│   ├── alembic/          # Database migrations
│   ├── tests/            # Pytest tests + fixtures
│   └── scripts/          # Seed and fixture scripts
├── frontend/
│   └── app/
│       ├── e1/ e2/ e3/ e4/ e5/   # Engine pages
│       ├── opportunities/         # Dashboard
│       ├── admin/                 # Admin dashboard
│       └── components/            # Shared components
└── BOMATIC_planning/              # Architecture docs + Codex prompts
```

---

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | — |
| `ANTHROPIC_API_KEY` | Anthropic API key for AI steps | — |
| `UPLOAD_DIR` | Directory for uploaded files | `storage` |
| `BOMATIC_API_KEY` | Static API key for backend access | — |
| `JWT_SECRET_KEY` | Secret for JWT signing | `change-me-in-production` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes | `480` |
