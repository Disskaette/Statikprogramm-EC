# Web Layer Details

## API (FastAPI, web/api/)

### Routes
- `POST /api/calculate` – full calculation (ec_modus true/false)
- `POST /api/calculate/deflection-only` – SLS only
- `GET  /api/materials/groups`, `/types`, `/klassen`, `/kmod`, `/psi`
- `GET/POST/PUT/DELETE /api/projects/*`
- `GET  /api/health` → `{"status":"ok","materials":"112","kmod_entries":"48"}`

### Project API – Extended Routes (Phase 6)
- `DELETE /{project_id}/positions/{path:path}`
- `PATCH  /{project_id}/positions/{path:path}/rename`
- `POST   /{project_id}/positions/{path:path}/duplicate`
- `PATCH  /{project_id}/positions/{path:path}/move`
- `POST   /{project_id}/folders`
- `DELETE /{project_id}/folders/{path:path}`
- ⚠️ Route ordering: specific sub-routes BEFORE catch-all `{path:path}` routes!
- list_positions returns `{positions:[...], folders:[...]}`

## React Frontend (web/frontend/src/)

### Tech Stack
- Vite + React 19 + TypeScript, tailwindcss @tailwindcss/vite
- zustand (store), @tanstack/react-query, katex, plotly.js-dist-min
- Path alias: `@/*` → `src/*`
- TS gotcha: `erasableSyntaxOnly: true` – no `public` constructor params

### Key Files
- `src/types/beam.ts` – TS interfaces (LoadCase, CrossSectionVariant, etc.)
- `src/types/project.ts` – Project + Position interfaces
- `src/stores/useBeamStore.ts` – Zustand store; buildRequest() assembles API payload
- `src/stores/useProjectStore.ts` – currentProjectId, currentPositionPath, isDirty
- `src/hooks/useMaterials.ts` – React Query for DB lookups (staleTime: Infinity)
- `src/hooks/useCalculation.ts` – useMutation with 600ms debounce
- `src/hooks/useProjects.ts` – useProjects() + usePositions(projectId)
- `src/hooks/useProjectActions.ts` – 11 actions: load/save/create/delete/rename/etc.
- `src/lib/format.ts` – parseGermanNumber, formatNumber
- `src/lib/api.ts` – typed fetch wrapper (get, post, put, patch, del)

### Components
- `src/components/input/` – CalculationModeToggle, SystemSection, LoadRow, LoadsSection, CrossSectionSection, DeflectionSection, InputForm
- `src/components/results/` – SchnittgroessenSummary, EC5NachweiseCard, LastkombinationenCard, ForceCharts, ResultsPanel
- `src/components/sidebar/ProjectExplorer.tsx` – full tree, context menu, drag&drop, multi-select
- `src/components/ui/` – ContextMenu, ConfirmDialog, InputDialog

### Patterns
- Local raw string state: useState(String(storeValue)) + onBlur resets
- JSON.stringify(...) as useEffect dep for object/array comparison
- KaTeX: strip `$...$` delimiters before renderToString(); `strict: false` for Unicode
- Unit conversions: Nmm÷1e6→kNm, N÷1e3→kN, mm stays mm
- DEFLECTION_PRESETS: Allgemein {300,200,300}, Überhöht {200,150,250}
- isDirty: setDirty(true) on form change, setDirty(false) on save/position load

### Plotly Charts (ForceCharts.tsx)
- Factory: `const Plot = createPlotlyComponent(Plotly)` at module level
- y-axis `autorange:'reversed'` (structural: positive moment downward)
- Theme colors from CSS vars inside useMemo([theme])
- System sketch: pure SVG

### Vite Config
- `base: process.env.VITE_BASE_URL ?? "/"` (set to `/statik/` in production)
- `optimizeDeps.include + build.commonjsOptions` for plotly.js-dist-min (CJS)

## Git Commit History
- `bf08b9d` fix: ImportError in tkinter stub (DEPLOYED, LIVE)
- `685fbb2` Phase 6 – Full project management (context menu, drag&drop, multi-select, folders)
- `ed838f0` Phase 5 – Project Explorer sidebar
- `c4a20e9` Phase 4 – Force diagrams (Plotly.js)
- `24b5326` Phase 3 – Results display (EC5, KaTeX, Lastkombis)
- `953a55e` Phase 2 – Complete input form (32+ fields)
- `e9614ca` Phase 1 – FastAPI + React foundation
