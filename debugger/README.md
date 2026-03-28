# Terra Cognitive Debugger

A pedagogical Python debugging tool designed to teach beginner programmers how to think about errors — not just fix them. Instead of showing answers immediately, the platform guides learners through a structured cognitive process: predict → run → reflect → hint → solution.

---

## What It Does

When a learner submits Python code, the platform:

1. **Executes it in an isolated sandbox** — a Docker container with no network, no shell access, capped CPU/memory, and a seccomp profile blocking process spawning.
2. **Classifies the error** — maps the exception type to a concept category (e.g. `NameError` → "Variable Initialization") and a cognitive skill (e.g. "State awareness") using a built-in taxonomy.
3. **Asks a reflection question** — forces the learner to think before they get help.
4. **Unlocks tiered hints** — three progressive hint tiers, each requiring the previous to be completed first.
5. **Reveals the solution** — only after all three hint tiers are exhausted (3 requests).
6. **Tracks metacognitive accuracy** — if the learner predicted the output before running, the platform compares prediction vs. actual and tracks accuracy over time.
7. **Shows a progress dashboard** — concept mastery, weakness profile, hint dependency ratio, and session history.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  Landing Page   │     │   React Frontend      │     │  FastAPI Backend  │
│  (Vite + TS)    │────▶│   (Vite + TS)         │────▶│  (Python 3.11)   │
│  Marketing site │     │   Monaco Editor       │     │  Async SQLAlchemy │
└─────────────────┘     │   Recharts dashboard  │     │  JWT + Redis      │
                        └──────────────────────┘     └────────┬─────────┘
                                                               │
                              ┌────────────────────────────────┤
                              │                                │
                    ┌─────────▼──────┐              ┌──────────▼──────────┐
                    │  PostgreSQL 15  │              │  Docker Sandbox      │
                    │  (all data)     │              │  (rootless DinD,     │
                    └────────────────┘              │   TLS, private net)  │
                                                    └─────────────────────┘
                    ┌────────────────┐
                    │  Redis 7        │
                    │  (JWT revoke,   │
                    │   OAuth state,  │
                    │   auth codes)   │
                    └────────────────┘
```

### Services (docker-compose)

| Service | Image | Purpose |
|---|---|---|
| `postgres` | postgres:15-alpine | Primary database |
| `redis` | redis:7-alpine | JWT revocation, OAuth state, one-time auth codes |
| `docker-sandbox` | docker:24-dind-rootless | Isolated code execution daemon (TLS-only, private network) |
| `sandbox-puller` | docker:cli | Pre-pulls `python:3.11-slim` into the sandbox on startup |
| `backend` | custom | FastAPI API server |
| `frontend` | custom | React app served via nginx |
| `pgadmin` | dpage/pgadmin4 | Dev-only DB admin UI (`--profile dev`) |

---

## Backend

**Stack:** FastAPI · SQLAlchemy (async) · Alembic · PostgreSQL · Redis · Docker SDK · python-jose · passlib/bcrypt

### Directory layout

```
backend/app/
├── api/v1/
│   ├── deps/          # auth_guard.py — JWT + session ownership checks
│   ├── routes/        # One file per feature area
│   │   ├── auth.py        # Email, GitHub OAuth, Google OAuth, anon sessions, merge
│   │   ├── execute.py     # Code submission, sandbox execution, classification
│   │   ├── reflect.py     # Reflection gate
│   │   ├── hint.py        # Tiered hint delivery
│   │   ├── solution.py    # Solution reveal (gated behind hints)
│   │   ├── analytics.py   # Concept stats, weakness profile, history
│   │   ├── session.py     # Session registration and token recovery
│   │   ├── export.py      # Data export
│   │   └── health.py      # Health check
│   └── schemas/       # Pydantic request/response models
├── cognitive/
│   └── engine.py      # Error parser, taxonomy classifier, hint/solution generators
├── core/
│   ├── auth.py        # JWT create/decode/revoke, bcrypt helpers
│   ├── config.py      # Pydantic Settings (env-driven)
│   ├── email.py       # SMTP verification email
│   └── redis_client.py
├── db/
│   ├── models.py      # All SQLAlchemy ORM models
│   ├── session.py     # Async engine + session factory
│   └── seed.py        # Concept categories + hint sequences seed data
├── execution/
│   └── service.py     # Docker sandbox runner
└── intelligence/
    ├── analytics_service.py  # Concept stats, weakness, session summary, snapshots
    └── prediction.py         # Prediction comparison + accuracy computation
```

### API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/anon` | Create anonymous session |
| `POST` | `/api/v1/auth/register` | Email registration (sends verification email) |
| `GET` | `/api/v1/auth/verify-email` | Email verification callback |
| `POST` | `/api/v1/auth/login` | Email login |
| `POST` | `/api/v1/auth/login-code` | Cross-origin login (returns one-time code) |
| `POST` | `/api/v1/auth/exchange` | Exchange one-time code for JWT |
| `GET` | `/api/v1/auth/github` | GitHub OAuth redirect |
| `GET` | `/api/v1/auth/github/callback` | GitHub OAuth callback |
| `GET` | `/api/v1/auth/google` | Google OAuth redirect |
| `GET` | `/api/v1/auth/google/callback` | Google OAuth callback |
| `GET` | `/api/v1/auth/me` | Rehydrate session identity from cookie |
| `POST` | `/api/v1/auth/logout` | Revoke JWT (Redis blacklist) + clear cookie |
| `POST` | `/api/v1/auth/merge` | Merge anonymous session into authenticated user |
| `POST` | `/api/v1/execute` | Submit code for execution + classification |
| `POST` | `/api/v1/reflect` | Submit reflection response (gates hint access) |
| `POST` | `/api/v1/hint` | Request a hint tier (1 → 2 → 3, sequential) |
| `POST` | `/api/v1/solution-request` | Request solution (revealed after 3 requests) |
| `GET` | `/api/v1/solution-request/{id}` | Read current solution state |
| `GET` | `/api/v1/analytics/concepts` | Concept error stats for session |
| `GET` | `/api/v1/analytics/weakness` | Concepts with ≥3 errors |
| `GET` | `/api/v1/analytics/session-summary` | Aggregate session stats |
| `GET` | `/api/v1/analytics/metacognitive` | Prediction accuracy metrics |
| `GET` | `/api/v1/analytics/history` | Paginated submission history with search |
| `POST` | `/api/v1/session/register` | Register a session and get an owner token |
| `POST` | `/api/v1/session/recover` | Rotate session token (requires current token) |
| `GET` | `/api/v1/health` | Health check |

### Cognitive engine (`cognitive/engine.py`)

The engine is pure Python with no external AI dependencies. It:

- **Parses tracebacks** with regex to extract exception type, message, and line number.
- **Classifies errors** against a 24-entry taxonomy mapping exception types to concept categories and cognitive skills.
- **Detects typos** using `difflib.get_close_matches` against Python builtins (e.g. `pint` → `print`).
- **Generates contextual hints** — per-exception-type lambdas that produce actionable, line-specific hint text.
- **Generates solution templates** — per-exception-type code examples with a list of specific changes needed.

### Sandbox security model

Every code submission runs in a fresh Docker container with:

- `network_disabled=True` — no outbound or inbound network
- `read_only=True` — filesystem is read-only except `/tmp`
- `tmpfs /tmp` — 16 MB, `noexec`
- `cap_drop=ALL` — all Linux capabilities dropped
- `user=nobody` — non-root execution
- `seccomp` profile — blocks `fork`, `vfork`, `clone`, `execve`, `execveat`
- Python-level deny wrapper — overrides `subprocess`, `os.system`, `os.popen`, `os.exec*` before user code runs
- 5-second timeout, 64 MB memory limit, 0.5 CPU quota
- Backend connects to a separate rootless DinD daemon over mutual TLS on a private Docker network — the host socket is never mounted

### Database models

| Table | Purpose |
|---|---|
| `users` | Registered users (email, GitHub, Google) |
| `anon_sessions` | Anonymous sessions |
| `session_ownership` | Maps session_id → server-issued owner token |
| `code_submissions` | Every submitted code snippet |
| `execution_results` | stdout, stderr, traceback, exit code, timing |
| `error_records` | Classified errors with concept category and cognitive skill |
| `concept_categories` | Seeded taxonomy of error concepts |
| `hint_sequences` | Three-tier hint text per concept category |
| `reflection_responses` | Learner reflection text (gates hint access) |
| `hint_events` | Audit log of every hint served (tier, text, line) |
| `solution_requests` | Tracks request count and reveal state per submission |
| `metacognitive_metrics` | Per-session prediction accuracy (correct/total) |
| `session_snapshots` | Daily aggregate stats per session |

---

## Frontend

**Stack:** React 18 · TypeScript · Vite · Monaco Editor · Recharts · Tailwind CSS · Playwright (E2E)

### Key components

| Component | Description |
|---|---|
| `App.tsx` | Root — auth state machine, session bootstrap, view routing |
| `EditorPanel` | Monaco-based Python editor |
| `RunButton` | Submission trigger with loading state |
| `OutputPanel` | Routes execution result to the correct output component |
| `ClassifiedError` | Displays classified error with reflection gate |
| `ReflectionGate` | Reflection text input — must be submitted before hints unlock |
| `HintTiers` | Progressive hint reveal (tier 1 → 2 → 3) |
| `SolutionGate` | Solution reveal after all hints exhausted |
| `SuccessOutput` | Success state with prediction match feedback |
| `UnclassifiedError` | Fallback for errors the engine can't classify |
| `HelpPanel` | Wraps the full hint/solution flow |
| `DashboardPage` | Progress overview with concept bar chart and session summary |
| `ConceptBarChart` | Recharts bar chart of concept mastery |
| `AuthModal` | Email + OAuth login/register modal |

### Auth flow

- On mount, `fetchMe()` hits `/auth/me` to rehydrate from the httpOnly cookie.
- If no valid cookie, an anonymous session is bootstrapped via `POST /auth/anon`.
- JWT is held **in a React ref only** (never localStorage) — the httpOnly cookie is the authoritative credential.
- Non-sensitive display data (username, avatar, session_id) is stored in localStorage for UI restoration.
- On login, anonymous session data is merged into the authenticated user via `POST /auth/merge`.
- OAuth flows use a one-time server-side code (stored in Redis) to avoid putting tokens in redirect URLs.

---

## Landing Page

A separate Vite + TypeScript marketing site (`landing/`) with components: Hero, Problem, Solution, HowItWorks, WhyItWorks, Gallery, Footer, Privacy. Has its own `LandingAuthModal` that uses the `login-code` endpoint for cross-origin login handoff to the tool frontend.

Live at: **https://terradebugger.me** (tool at **https://terradebugger.me/app**)

> **Important:** `FRONTEND_URL` in the backend `.env` must be set to `https://terradebugger.me/app` (not the landing root). This is where OAuth callbacks redirect after login. Setting it to the landing root will cause the `?code=` param to land on the wrong page.

> **Rebuild note:** The landing Docker image caches aggressively. Always use `--no-cache` when rebuilding after source changes:
> ```bash
> docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache landing
> ```

---

## CI/CD

Two GitHub Actions workflows in `.github/workflows/`:

- `deploy-backend.yml` — builds and deploys the backend
- `deploy-frontend.yml` — builds and deploys the frontend

---

## Local Development Setup

### Prerequisites

- Docker Desktop (with Docker Compose)
- Node.js 20+
- Python 3.11+

### 1. Clone and configure

```bash
git clone <repo-url>
cd debugger
cp .env.example .env
```

Edit `.env` — at minimum set:

```env
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(64))">
DATABASE_URL=postgresql+asyncpg://debugger:debugger@localhost:5432/debugger
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=yourpassword
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:5173
ENV=development
DEV_SKIP_EMAIL=true
```

### 2. Start all services

```bash
docker compose up --build
```

This starts PostgreSQL, Redis, the rootless Docker sandbox daemon, the backend (with DB seed), and the frontend.

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs (dev only): http://localhost:8000/docs
- pgAdmin (dev profile): `docker compose --profile dev up` → http://localhost:5050

### 3. Run backend locally (without Docker)

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 4. Run frontend locally

```bash
cd frontend
npm install
npm run dev
```

### 5. Run tests

```bash
# Backend
cd backend
pytest tests/

# Frontend unit tests
cd frontend
npm test

# Frontend E2E
npm run test:e2e
```

---

## Production Deployment

1. Set `ENV=production` — disables `/docs`, `/redoc`, enables `Secure` cookie flag, sets log level to INFO.
2. Generate a strong `JWT_SECRET_KEY`.
3. Configure SMTP credentials for email verification.
4. Configure `GITHUB_CLIENT_ID/SECRET` and/or `GOOGLE_CLIENT_ID/SECRET` for OAuth.
5. Set `ALLOWED_ORIGINS` to your frontend domain.
6. Set `FRONTEND_URL` to `https://yourdomain.com/app` — **not** the landing root. OAuth callbacks redirect here.
7. Use `docker-compose.prod.yml` for production overrides.
8. The sandbox daemon (`docker-sandbox`) must be reachable from the backend over the private `sandbox-net` network with mutual TLS — do not expose it publicly.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async connection string |
| `JWT_SECRET_KEY` | ✅ | HS256 signing key — server refuses to start if default |
| `REDIS_URL` | ✅ | Redis connection URL |
| `REDIS_PASSWORD` | ✅ | Redis auth password |
| `ENV` | ✅ | `development` or `production` |
| `FRONTEND_URL` | ✅ | Used for OAuth redirects and email links |
| `BACKEND_URL` | ✅ | Used for OAuth callback registration |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated CORS + CSRF allowed origins |
| `GITHUB_CLIENT_ID` | optional | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | optional | GitHub OAuth app client secret |
| `GOOGLE_CLIENT_ID` | optional | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | optional | Google OAuth client secret |
| `SMTP_HOST` | optional | SMTP server for verification emails |
| `SMTP_PORT` | optional | Default: 587 |
| `SMTP_USER` | optional | SMTP username |
| `SMTP_PASSWORD` | optional | SMTP password |
| `EMAIL_FROM` | optional | From address for verification emails |
| `DEV_SKIP_EMAIL` | optional | `true` to skip email sending in development |
| `SANDBOX_IMAGE` | optional | Default: `python:3.11-slim` |
| `SANDBOX_TIMEOUT_SECONDS` | optional | Default: 5 |
| `SANDBOX_MEM_LIMIT` | optional | Default: `64m` |
| `SANDBOX_CPU_QUOTA` | optional | Default: `500000000` (0.5 CPU) |
| `SANDBOX_SECCOMP_PROFILE` | optional | Path to seccomp JSON profile |
| `MAX_CODE_LENGTH` | optional | Default: 10000 characters |

---

## Security Notes

- **CSRF protection** — Origin/Referer header validation on all cookie-authenticated mutation endpoints.
- **JWT revocation** — Logout stores the JTI in Redis with a 7-day TTL; all protected routes check the blacklist.
- **Session ownership** — Every session-scoped request validates that the caller's JWT `sub` matches the session ID.
- **Rate limiting** — slowapi limits on execute (30/min), register (5/min), login (10/min), anon (20/min).
- **Password policy** — minimum 8 characters, at least one letter and one digit, max 72 bytes (bcrypt limit).
- **OAuth state** — CSRF-protected with a Redis-backed one-time state token (10-minute TTL).
- **Auth codes** — OAuth and cross-origin login use server-side one-time codes (5-minute TTL) instead of putting tokens in redirect URLs.
