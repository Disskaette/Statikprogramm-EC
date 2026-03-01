# Developer Dave - Agent Memory

## Project Overview
- **App**: Durchlaufträger (continuous beam calculator) for timber design per EC5/EC0/EC1
- **Current State**: Python + CustomTkinter desktop app (v2.0), migration to web planned
- **Entry Point**: `main_v2.py`
- **Target**: Integration into `stark-tools` web portal at `tools.askbenstark.com`

## Key Architecture
- **Backend** (UNTOUCHABLE without approval): `backend/` - calculations, database, services, project mgmt
- **Frontend** (TO MIGRATE): `frontend/` - CustomTkinter GUI, display modules, input masks
- **Calculation Flow**: Input → OrchestratorService → LoadCombos → FEEBB (FEM) → EC5 Verification → Display
- See [project-structure.md](project-structure.md) for full details

## stark-tools Integration
- **Tech Stack**: Docker Compose + nginx reverse proxy + Flask auth (cookie sessions)
- **Auth**: 3 users: `stark` (mitarbeiter), `admin` (admin), `felix_k` (felix)
- **Existing tools**: Holzlisten-Generator (Streamlit/8501), Sortierprozess (8502)
- **Deploy**: GitHub Actions → SSH → Docker on Hetzner VPS
- **Portal**: `auth/app.py` has KACHELN list for tool cards + role-based visibility
- See [stark-tools-integration.md](stark-tools-integration.md) for details

## User Preferences
- Communication: German with user, English in code/comments
- Backend calc logic: NEVER change without explicit approval
- Approach: Analyze first, propose, get approval, then implement
- Priority: Correctness > Readability > Maintainability > Performance

## Key Files
- `backend/calculations/feebb.py` - FEM solver (Euler-Bernoulli)
- `backend/calculations/feebb_schnittstelle_ec.py` - EC pattern-loading (~1330 lines)
- `backend/calculations/nachweis_ec5.py` - EC5 design checks (bending, shear, deflection)
- `backend/calculations/lastenkombination.py` - ULS load combinations
- `backend/calculations/lastkombination_gzg.py` - SLS load combinations
- `backend/database/datenbank_holz.py` - Timber material DB (C14-C50, GL24h-GL32h)
- `backend/service/orchestrator_service.py` - Calculation pipeline coordinator
- `frontend/gui/eingabemaske.py` - Main input form (LEGACY, needs migration)
- `frontend/display/anzeige_*.py` - 4 display modules (system, forces, combis, EC5)
- `frontend/modules/modul_durchlauftraeger.py` - Main calculation module
- `config/settings.json` - App settings (recent projects, geometry, theme)

## Web API Layer (NEW – Tasks 1-5 completed)
- **Location**: `web/` directory – does NOT modify `backend/`
- **Framework**: FastAPI + uvicorn, started with `uvicorn web.api.main:app`
- **Requires Python 3.12+** (nachweis_ec5.py line 288 uses backslash-in-f-string, only valid ≥ 3.12)
- **Routes**: `/api/calculate`, `/api/calculate/deflection-only`, `/api/materials/*`, `/api/projects/*`, `/api/health`
- `web/api/deps.py` – sys.path patch + tkinter no-op stubs + singleton DB/ProjectManager
- `web/api/main.py` – FastAPI app, CORS, lifespan DB pre-load, static SPA serving
- `web/api/routes/calculation.py` – bridges callback-based OrchestratorService to asyncio Future
- `web/api/routes/materials.py` – read-only DB lookups (groups, types, kmod, ψ-values)
- `web/api/routes/projects.py` – CRUD for projects + positions via ProjectManager

## Critical Snapshot Format Rules
- `snapshot['wert']` (each load) MUST be **STRING** – validation_service: `wert not in (None, "")`
- `snapshot['sprungmass']` can be **FLOAT** – lastenkombination.py uses it as multiplier directly
- `snapshot['lasten']` each entry MUST include `kommentar` key (feebb_schnittstelle.py accesses it)
- `snapshot['gebrauchstauglichkeit']` keys MUST use `_grenz` suffix: `w_inst_grenz`, `w_fin_grenz`, `w_net_fin_grenz`
- `I_y` = b*h³/12 [mm⁴], `W_y` = I_y/(h/2) [mm³] – computed in `CalculationRequest.to_snapshot()`
- E-modulus from `db.get_emodul(gruppe, typ, klasse)` [N/mm²]
- Load categories MUST exactly match DB values (e.g. "Nutzlast Kat. A: Wohnraum" NOT "Wohn- und Aufenthaltsräume")

## Known Issues / Pitfalls
- `feebb_schnittstelle.py` imports `tkinter` + `FigureCanvasTkAgg` at module level (dead imports)
  → Fixed in `web/api/deps.py::_install_tkinter_stubs()` – injects no-op sys.modules stubs
- Project `.venv` uses Python 3.10 – NOT compatible; always start API with Python 3.12+
- OrchestratorService debounce: reset `_last_hash=None, _last_time=0.0` before each API call
  → Done automatically in `web/api/routes/calculation.py::_run_orchestrator()`
- Backend returns numpy types (float64, bool_, ndarray) → must convert to native Python before JSON serialisation
  → `_convert_numpy_types()` in `web/api/routes/calculation.py` handles this recursively
- Internal units: Moments in [Nmm], Forces in [N], Deflections in [mm] – frontend must convert for display

## API Status (✅ Fully Working)
- POST /api/calculate – both ec_modus=false (quick) and ec_modus=true (pattern loading) verified
- GET /api/health, /api/materials/* – all working
- POST /api/calculate/deflection-only – implemented, not yet tested

## React Frontend (NEW – Scaffolded)
- **Location**: `web/frontend/` – Vite + React 19 + TypeScript
- **Node.js**: Installed via Homebrew (v25.6.1); binary at `/opt/homebrew/bin/node`
  - Always use `export PATH="/opt/homebrew/bin:..."` in bash commands
- **Key deps**: tailwindcss @tailwindcss/vite, katex, plotly.js-dist-min, react-plotly.js,
  zustand, @tanstack/react-query, react-icons, react-resizable-panels, clsx, tailwind-merge
- **Vite proxy**: `/api` → `http://localhost:8000` (dev mode)
- **Path alias**: `@/*` → `src/*` (configured in tsconfig.app.json + vite.config.ts)
- **CSS vars**: Light/dark theme via CSS custom properties in `src/index.css`
- **Lib files**: `src/lib/utils.ts` (cn helper), `src/lib/api.ts` (typed fetch wrapper)
- **Directories**: `src/components/{ui,layout,input,results}`, `src/hooks`, `src/stores`, `src/types`
- **TS Gotcha**: `erasableSyntaxOnly: true` in tsconfig – cannot use `public` constructor params;
  must declare class fields explicitly (affects ApiError and any future classes)
- **Build**: `npm run build` → `dist/` (503ms, zero errors verified)
