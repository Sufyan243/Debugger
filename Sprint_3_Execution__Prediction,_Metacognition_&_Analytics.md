# Phase Breakdown



## Task 4: Phase 4 — Analytics & Export API Endpoints

Expose the intelligence layer via REST endpoints and register them in `d:\SAAS\Debugger\debugger\backend\app\main.py`:

- Create debugger/backend/app/api/v1/routes/analytics.py with:
  - `GET /api/v1/analytics/concepts?session_id=` → calls `get_concept_stats()`
  - `GET /api/v1/analytics/weakness?session_id=` → calls `get_weakness_profile()`
  - `GET /api/v1/analytics/session-summary?session_id=` → calls `get_session_summary()` and persists a `SessionSnapshot`
  - `GET /api/v1/analytics/metacognitive?session_id=` → returns `MetacognitiveMetric` for the session
- Create debugger/backend/app/api/v1/routes/export.py with:
  - `GET /api/v1/export/session/{session_id}` — returns JSON + CSV (use Python stdlib `csv` + `io.StringIO`, no new packages) of submissions, errors, reflections, predictions, hints
- Create matching Pydantic response schemas in `d:\SAAS\Debugger\debugger\backend\app\api\v1\schemas` (e.g. `analytics.py`, `export.py`)
- Register both routers in `d:\SAAS\Debugger\debugger\backend\app\main.py`


## Task 5: Phase 5 — Analytics Dashboard (Frontend)

Build the `/dashboard` view and wire it to the analytics API — **no new router package needed** (use a simple state-based view toggle in `d:\SAAS\Debugger\debugger\frontend\src\App.tsx`):

- Add `recharts@2.12.x` to `d:\SAAS\Debugger\debugger\frontend\package.json` (compatible with React 18, no conflicts)
- Extend `d:\SAAS\Debugger\debugger\frontend\src\api\client.ts` with `fetchConceptStats`, `fetchWeaknessProfile`, `fetchSessionSummary`, `fetchMetacognitive` functions
- Create debugger/frontend/src/hooks/useDashboard.ts hook that calls all four analytics endpoints
- Create debugger/frontend/src/components/Dashboard/DashboardPage.tsx with four sections:
  1. **Concept Mastery** — progress bars (`███░░ 70%`) per concept
  2. **Weakness Areas** — list of weak concepts with error counts
  3. **Prediction Accuracy** — metacognitive score display
  4. **Session Summary** — submissions / errors / hints used / concepts learned
- Create debugger/frontend/src/components/Dashboard/ConceptBarChart.tsx using `recharts` `BarChart` (errors per concept)
- Toggle between Editor and Dashboard views via the existing "My Progress" nav link in `d:\SAAS\Debugger\debugger\frontend\src\App.tsx` (add a `view` state: `"editor" | "dashboard"`)