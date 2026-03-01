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
- **Build**: `npm run build` → `dist/` (zero errors verified)
- **Types**: `src/types/beam.ts` – all TS interfaces (LoadCase, CrossSectionVariant, DeflectionLimits, CalculationRequest/Response, EC5Nachweis)
- **Store**: `src/stores/useBeamStore.ts` – Zustand store, single source of truth for form state; buildRequest() assembles API payload
- **Hooks**: `src/hooks/useMaterials.ts` – React Query hooks (staleTime: Infinity) for DB lookups
- **Hooks**: `src/hooks/useCalculation.ts` – useMutation hook with 600ms debounce; writes results to store
- **DEFLECTION_PRESETS**: exported const in beam.ts – Allgemein: {300,200,300}, Überhöht: {200,150,250}
- **buildRequest() NKL convention**: cross-section NKL taken from lasten[0].nkl (all loads share same service class)

## Input Form Components (Phase 2 completed, build ✅)
- `src/lib/format.ts` – parseGermanNumber("7,41" → 7.41), formatNumber(de-DE locale)
- `src/components/input/CalculationModeToggle.tsx` – pill toggle, ecModus true/false
- `src/components/input/SystemSection.tsx` – Sprungmaß, Feldanzahl stepper, Kragarme, dynamic SpanRow sub-component with local raw string state
- `src/components/input/LoadRow.tsx` – single load row with cascading lastfall→kategorie dropdowns; useEffect auto-selects first kategorie when lastfall changes
- `src/components/input/LoadsSection.tsx` – loads table + NKL global selector (updates all loads) + Eigengewicht checkbox (finds first g-load by index)
- `src/components/input/CrossSectionSection.tsx` – 3 variant columns (VariantColumn sub-component) with cascading materialgruppe→typ→festigkeitsklasse + dimension inputs
- `src/components/input/DeflectionSection.tsx` – situation dropdown switches between presets (read-only) and "Eigene Werte" (editable); rawValues state synced via useEffect on situation change
- `src/components/input/InputForm.tsx` – assembles all sections; auto-triggers calculation via useEffect watching JSON.stringify of store slices; skips first render via useRef(true)
- Pattern for local raw string: useState(String(storeValue)) + onChange updates raw + store, onBlur resets raw to String(storeValue)
- JSON.stringify(...) used as useEffect dependency for object/array comparison (pragmatic, avoids deep-equal library)

## Results Display Components (Phase 3 completed, tested ✅, committed)
- `src/index.css` – adds `@import "katex/dist/katex.min.css"` (KaTeX fonts bundled by Vite)
- `src/components/results/SchnittgroessenSummary.tsx` – compact horizontal card: M_Ed [kNm], V_Ed [kN], δ_max [mm] with KaTeX inline symbols
- `src/components/results/EC5NachweiseCard.tsx` – 5 verification checks (biegung, schub, 3 deflection checks); utilisation bar green/amber/red; KaTeX display formula per check
- `src/components/results/LastkombinationenCard.tsx` – collapsible, tabbed GZT/GZG load combinations; maßgebend badge; KaTeX formula per combination
- `src/components/results/ResultsPanel.tsx` – main container: empty state, loading spinner, recalculating overlay, composes all result sub-components
- `src/App.tsx` – two-column layout (lg:flex-row): input left (xl:w-2/5), results right (xl:w-3/5)
- KaTeX LaTeX stripping: API wraps all formulae in `$…$`; must call `stripDelimiters()` before `katex.renderToString()` – handles both `$` and `$$`
- **KaTeX strict:false** – backend LaTeX uses Unicode ² (N/mm²); `strict: false` suppresses warnings
- Bar width formula: `min(eta / 1.5, 1) * 100%` – caps visual bar at 150% η so extreme failures remain readable
- Unit conversions: Moments Nmm→kNm (÷1e6), Forces N→kN (÷1e3), Deflections stay mm – GZT for M/V, GZG for δ

## Force Diagrams (Phase 4 completed, build ✅)
- `src/components/results/ForceCharts.tsx` – Plotly charts: system sketch (SVG) + M, V, w diagrams
- `src/plotly-dist-min.d.ts` – ambient module declaration re-exporting from `plotly.js` types
  (plotly.js-dist-min has no bundled .d.ts; @types/plotly.js is installed via @types/react-plotly.js)
- Plotly factory pattern: `const Plot = createPlotlyComponent(Plotly)` – must be at module level (not inside component)
- All 3 diagrams: y-axis `autorange: 'reversed'` (structural engineering convention, positive moment downward)
- Theme colors read via `getComputedStyle(document.documentElement).getPropertyValue('--foreground')` etc.
  → Re-read inside `useMemo(..., [theme])` so charts update when user switches light/dark
- GZG deflection: iterate GZG array, find entry with max |durchbiegung|; fall back to GZT
- Unit conversions in chart data: moment Nmm÷1e6→kNm, shear N÷1e3→kN, deflection mm stays mm
- System sketch: pure SVG (not Plotly) – beam line, filled triangles for supports, field labels, dimension lines
- Support positions: field boundary x-coords excluding cantilever free ends
- Field boundary x-coords used both for SVG tick marks AND Plotly shape vertical dashed lines
- ResultsPanel: ForceCharts rendered in a `<section>` between EC5NachweiseCard and LastkombinationenCard

## Project Explorer / Phase 5 (completed, build ✅, browser tested ✅, committed ed838f0)
- `src/types/project.ts` – Project + Position interfaces
- `src/stores/useProjectStore.ts` – Zustand store: currentProjectId, currentPositionPath, isDirty
- `src/hooks/useProjects.ts` – React Query: useProjects() + usePositions(projectId), staleTime: 30_000
- `src/hooks/useProjectActions.ts` – loadPosition(), savePosition(), createPosition(); invalidates query cache
- `src/components/sidebar/ProjectExplorer.tsx` – sidebar: project dropdown, position list grouped by subfolder, save/new-position bar
- `src/components/sidebar/` directory created
- **loadFromRequest** added to useBeamStore – bulk-updates all form fields from CalculationRequest shape
  - Derives feldanzahl + kragarm flags by counting/inspecting keys in req.spannweiten
  - Replicates active variant to all 3 variant slots; resets activeVariant = 1
  - Sets deflection.situation = "Eigene Werte" (saved positions don't store preset label)
  - Always clears results + calculationError after loading
- **isDirty tracking**: InputForm.tsx useEffect now calls setDirty(true) on any form change
  - setDirty(false) called by savePosition() after successful PUT
  - setDirty(false) called by setCurrentPosition() in useProjectStore
- **Position save format**: PUT body = `{modules: {durchlauftraeger: <CalculationRequest>}, active_module: "durchlauftraeger"}`
- **Vite fix**: Added `optimizeDeps.include` + `build.commonjsOptions` for `plotly.js-dist-min` (CJS module without ES default export was causing Rollup build failure)
- **Subfolder grouping**: getSubfolder() splits relativePath on "/" – root-level positions get folder=""
- **Dirty indicator**: amber dot (●) next to position name in sidebar bottom bar when isDirty
- **Edge case**: Positions with `durchlauftraeger: null` don't reset form (loadFromRequest skipped)
  → Known limitation, acceptable for now; form retains previous values

## Projects API – Extended Routes (Phase 6, browser tested ✅)
- **New endpoints** (all in `web/api/routes/projects.py`):
  - `DELETE /{project_id}/positions/{path:path}` – delegates to `pm.delete_position()`
  - `PATCH  /{project_id}/positions/{path:path}/rename` – updates JSON + renames file + syncs project.json
  - `POST   /{project_id}/positions/{path:path}/duplicate` – shutil.copy2 + `_Kopie[_N]` suffix + syncs project.json
  - `PATCH  /{project_id}/positions/{path:path}/move` – shutil.move + creates target dir + syncs project.json
  - `POST   /{project_id}/folders` – mkdir(parents=True, exist_ok=False) + path traversal guard
  - `DELETE /{project_id}/folders/{path:path}` – shutil.rmtree + cleans project.json positions
- **list_positions** now returns `{positions: [...], folders: [...]}` (was plain list)
- **Path traversal guard**: `_assert_inside_project()` – resolved_path.resolve().relative_to(project_path.resolve())
- **Filename generation**: `_build_position_filename()` mirrors `PositionModel.get_filename()` exactly
- All operations: open_project(project_path) before pm calls, run_in_executor for sync I/O
- **⚠️ CRITICAL: Route ordering** – specific sub-routes (rename, duplicate, move) MUST be registered
  BEFORE the catch-all `{position_path:path}` routes. Otherwise FastAPI absorbs the suffix into
  the path parameter and returns 405 Method Not Allowed. Fixed by reordering routes in projects.py.

## Project Explorer – Full Features (Phase 6, browser tested ✅)
- `src/components/sidebar/ProjectExplorer.tsx` – ~850 lines, complete rewrite from Phase 5
- **Tree View**: `buildFolderTree(positions, folders)` → recursive `FolderNode` tree; `FolderGroup` recursive component
- **Context Menu**: position (Öffnen, Neuer Ordner, Umbenennen, Duplizieren, Löschen), folder (Neuer Ordner, Löschen), multi-select (Löschen N Elemente)
- **Multi-Select**: Click (single), Ctrl/Cmd+Click (toggle), Shift+Click (range via visiblePaths + anchor ref)
- **Drag & Drop**: Manual mouse events (mousedown/mousemove/mouseup), 5px threshold, `data-folder-path` attributes for drop targets
- **Dialog state**: Union type `DialogState` with variants for each dialog type
- **Sub-components**: PositionItem, FolderGroup (recursive), InlineInput, NewPositionForm
- `src/hooks/useProjectActions.ts` – 11 actions: load/save/create/delete/rename/duplicate/move + bulk delete + folder create/delete
- `src/hooks/useProjects.ts` – handles both old (Position[]) and new ({positions, folders}) response format
- **Unicode gotcha**: Subagents may write `\u00f6` instead of `ö` – always check and replace unicode escapes in German text

## Git Commit History (Web Migration)
- `685fbb2` Phase 6 – Full project management (context menu, drag&drop, multi-select, folders)
- `ed838f0` Phase 5 – Project Explorer sidebar
- `c4a20e9` Phase 4 – Force diagrams (Plotly.js)
- `24b5326` Phase 3 – Results display (EC5, KaTeX, Lastkombis)
- `953a55e` Phase 2 – Complete input form (32+ fields)
- `e9614ca` Phase 1 – FastAPI + React foundation

## UI Component Library (src/components/ui/)
- `ContextMenu.tsx` – portal via ReactDOM.createPortal; boundary detection; dismiss: mousedown outside (capture), Escape (capture), scroll (capture)
- `ConfirmDialog.tsx` – native `<dialog>` + showModal()/close(); danger prop = red button; backdrop click closes
- `InputDialog.tsx` – native `<dialog>`; auto-focus + select on open via requestAnimationFrame; Enter submits, empty input disables confirm
- **Pattern**: useEffect on `open` prop calls dialog.showModal()/close(); separate useEffect intercepts "cancel" event (Escape) to call onCancel instead of browser default
- `api.ts` – has get, post, put, patch, delete, del (alias for delete)
- `FolderNode` interface in `src/types/project.ts` – recursive tree for explorer
- `useProjectStore` – selectedPaths (string[]), isDragging, dragPaths + toggleSelection(path, multiSelect), clearSelection(), setDragging(bool, paths?)

## Production Deployment (stark-tools Portal)

- **URL**: `https://tools.askbenstark.com/statik/`
- **Container**: `stark-statik` (python:3.12-slim, FastAPI + React SPA, Port 8000)
- **Deploy**: `.github/workflows/deploy.yml` in DIESEM Repo, Trigger: push auf main
  → NICHT Teil von stark-tools docker-compose.yml (eigener unabhängiger Deploy!)
- **Repo auf VPS**: `/root/statikprogramm/` (geclont von Disskaette/Statikprogramm-EC)
- **Netzwerk**: Docker-Bridge `stark-tools` (geteilt mit stark-nginx, stark-auth etc.)
- **Sub-Path-Routing**: nginx proxied `/statik/` → FastAPI `:8000/` (trailing slash strippt Präfix)
- **Vite**: `VITE_BASE_URL=/statik/` (assets), `VITE_API_BASE_URL=/statik` (API-Calls)
  → Diese Build-Args sind im Dockerfile als ARG/ENV definiert; NIEMALS entfernen!
- **Projekte**: Volume-Mount `/root/statikprogramm/Projekte/` → `/app/Projekte/`
- **Rollen**: `felix` (felix_k) + `admin` sehen die Kachel
- **Dockerfile**: Multi-Stage (node:22-alpine für Vite-Build, python:3.12-slim für Runtime)
- **Secrets im Repo nötig**: `SSH_HOST`, `SSH_USER`, `SSH_KEY` (Settings → Secrets → Actions)

## Critical API Response Format Pitfalls
- **schnittgroessen.GZT**: Object `{max: {moment, querkraft, durchbiegung}, moment: [...], ...}`
- **schnittgroessen.GZG**: **ARRAY** `[{max: {durchbiegung}, lastfall, kommentar, moment: [...], ...}]` – one entry per load
  - Must iterate array to find max deflection; GZG max only has `durchbiegung`, not moment/querkraft
- **lastfallkombinationen keys**: LaTeX strings like `\gamma_{g} \cdot g` – must render via KaTeX, not display raw
- **ec_modus=false** with only permanent load: backend may error on `kmod_g` if no variable load exists
