# Developer Dave - Agent Memory

## Project Status: LIVE ✅
- **App**: Durchlaufträger (continuous beam calculator) EC5/EC0/EC1
- **Migration**: DONE – desktop Tkinter app removed (v1.2.0), web app is live
- **URL**: https://tools.askbenstark.com/statik/ (admin + felix_k)
- **Tags**: v1.0.0 (initial), v1.1.0 (cleanup), v1.2.0 (legacy removal)
- **Repo**: Disskaette/Statikprogramm-EC

## Key Architecture
- **Backend** (UNTOUCHABLE): `backend/` – FEM, EC5, load combos, materials, project mgmt
- **Web API**: `web/api/` – FastAPI + uvicorn, Python 3.12 required
- **Frontend**: `web/frontend/` – Vite + React 19 + TypeScript (fully built)
- **Calculation Flow**: Input → OrchestratorService → LoadCombos → FEEBB → EC5 → JSON

## User Preferences
- German with user, English in code/comments
- Backend calc logic: NEVER change without explicit approval
- Approach: Analyze first, propose, get approval, implement
- Priority: Correctness > Readability > Maintainability > Performance

## Key Files
- `backend/calculations/feebb.py` – FEM solver (Euler-Bernoulli)
- `backend/calculations/feebb_schnittstelle_ec.py` – EC pattern-loading (~1330 lines)
- `backend/calculations/nachweis_ec5.py` – EC5 design checks (Python 3.12+)
- `backend/database/datenbank_holz.py` – Timber material DB (C14-C50, GL24h-GL32h)
- `backend/service/orchestrator_service.py` – Calculation pipeline coordinator
- `web/api/deps.py` – sys.path patch + tkinter stubs + singleton DB/ProjectManager
- `web/api/main.py` – FastAPI app, CORS, static SPA serving
- `web/api/routes/calculation.py` – bridges OrchestratorService to asyncio Future
- `web/api/routes/projects.py` – CRUD projects + positions + PATCH visibility
- `web/frontend/src/` – React app
- `web/frontend/src/fs/useLocalFileSystem.ts` – File System Access API wrapper
- `web/frontend/src/lib/localHandleStorage.ts` – IndexedDB handle persistence (idb-keyval)
- `web/frontend/src/stores/useLocalProjectStore.ts` – local project state
- `web/frontend/src/hooks/useLocalProjectActions.ts` – load/save/create/delete/sync local
- See [web-layer.md](web-layer.md) for full API + React component details

## Local File Management Feature (shipped 2026-03-06)
- **File System Access API**: `showDirectoryPicker()` → real local folder on disk
- **IndexedDB**: handles persisted via `idb-keyval` store `"statik-local"/"handles"`
- **Auto-save routing**: `useProjectStore.currentProjectMode` = `"server"|"local"` → `useAutoSave` routes to API or disk
- **ProjectExplorer**: Server/Lokal tabs; LocalTab lists opened folders
- **Sync**: Local→Server (☁↑ upload dialog, visibility choosable); Server→Local (☁↓ download)
- **Visibility**: `project.json` gets `visibility: "private"|"shared"` (default private); `PATCH /api/projects/{id}/visibility`
- **Folder structure**: identical to server (copy-paste in Finder works)
- **Browser support**: Chrome 86+, Edge 86+, Firefox 111+; graceful error for others
- **Pitfall**: `from __future__ import annotations` in projects.py means linters may remove `Literal` import if they don't see it used at runtime – always check after linter runs

## Critical Pitfalls

### tkinter Stub Bug (FIXED in bf08b9d)
`web/api/deps.py::_install_tkinter_stubs()` MUST catch `ImportError` not `ModuleNotFoundError`.
On `python:3.12-slim`, tkinter module exists but `libtk8.6.so` is missing → raises `ImportError`.
`ModuleNotFoundError` is a subclass and does NOT catch this.

### Snapshot Format Rules
- `snapshot['wert']` (loads) MUST be **STRING**
- `snapshot['lasten']` each entry MUST include `kommentar` key
- `snapshot['gebrauchstauglichkeit']` keys: `w_inst_grenz`, `w_fin_grenz`, `w_net_fin_grenz`
- `I_y` = b*h³/12 [mm⁴], `W_y` = I_y/(h/2) [mm³] – computed in CalculationRequest.to_snapshot()
- Load categories MUST match DB values exactly

### Other Pitfalls
- Python 3.12 required (nachweis_ec5.py uses f-string backslash, invalid in 3.10)
- OrchestratorService debounce: reset before each API call (done in calculation.py)
- numpy types must be converted before JSON (done by _convert_numpy_types())
- Units: Moments [Nmm], Forces [N], Deflections [mm] – convert in frontend

## Deploy Architecture (stark-tools portal)

### How stark-statik is deployed
1. Push to main in Statikprogramm-EC → GitHub Actions `.github/workflows/deploy.yml`
2. SSH to VPS, git pull to `/root/statikprogramm/`
3. `docker build --build-arg VITE_BASE_URL=/statik/ --build-arg VITE_API_BASE_URL=/statik`
4. `docker run --network stark-tools --name stark-statik -v /root/statikprogramm/Projekte:/app/Projekte`
5. Health check: `curl http://<container-ip>:8000/api/health` with retry

### Deploy Lessons (do NOT redo these mistakes)
- **Network**: `docker-compose.yml` uses `external: true` for `stark-tools` network. Deploy script creates it manually first: `docker network create stark-tools 2>/dev/null || true`
- **Container conflict**: Stop/rm old containers BEFORE compose up (non-compose containers cause "name already in use")
- **git pull on VPS**: Use `git fetch + git reset --hard FETCH_HEAD` (not `git pull`) – VPS may have local edits
- **Health check**: Container is up but uvicorn takes ~5-10s to start. Use `curl --retry` not `docker exec python3`

### Sub-path routing
nginx strips `/statik/` before FastAPI using `rewrite ^/statik/(.*) /$1 break;` + `proxy_pass http://$upstream:8000;` (NO trailing slash).
Vite MUST be built with `VITE_BASE_URL=/statik/` and `VITE_API_BASE_URL=/statik` (build args in Dockerfile).

### CRITICAL nginx pitfall: variable upstream + trailing slash = broken path stripping
`proxy_pass http://$upstream:8000/;` with a variable (`set $upstream ...`) does NOT strip the
location prefix – every request arrives as `GET /` at the upstream, regardless of the actual path.
This is a known nginx bug/behavior (https://trac.nginx.org/nginx/ticket/1067).
FIX: Use `rewrite ^/PREFIX/(.*) /$1 break;` + `proxy_pass http://$upstream:PORT;` (no trailing slash).
Other locations (holzlisten, joerg, co2) correctly omit the trailing slash – only statik had this bug.

## Batched FEM Solve (commit 8f61369, 2026-03-07)

### Problem & Fix
EC mode was returning empty `schnittgroessen: {}` and `ec5_nachweise: {}` (silent 200).
Root cause: `_fuehre_postprocessing` (new batch path) was missing the `"max"` key.
`_erstelle_detaillierte_kombinationsergebnisse` accesses `x["max"]["moment"]` → KeyError.
KeyError caught by `add_section_forces` bare `except Exception` → returned `{}`.

**Fix**: Added `"max"` dict to `_fuehre_postprocessing` return value (identical computation
to the sequential `_fuehre_feebb_berechnung_durch` method).

### Batch Solve Architecture
- `Beam(elements, supports, lazy_solve=True)` – assembles K+F but skips solve
- `np.linalg.solve(K, F_matrix)` – ONE LU factorisation for ALL load combos
- Speedup: 90 sequential solves (291ms) → 1 batched solve (6ms) → **51× faster**
- Tests: `tests/test_batched_fem_solve.py` covers `_berechne_alle_kombinationen`
  but NOT `compute()` – so tests pass even if `_erstelle_detaillierte_kombinationsergebnisse` breaks
- Silent exception swallow in `calculation_service.py` line 53: `except Exception: return {}`
  → ALWAYS adds logging + check ec5_nachweise is non-empty when debugging EC issues

## GZG Deflection Checks (commit c776928, 2026-03-08)

### Three bugs fixed in `nachweis_ec5.py` + `feebb_schnittstelle_ec.py`

**1 – w_fin base: characteristic → quasi-permanent (EC5 §2.2.3)**
- Old: `delta_end = (1+kdef) * max(all GZG)` → applied kdef to characteristic (G+Q)
- Fix: `feebb_schnittstelle_ec.py` stores `gzg_envelope["max"]["durchbiegung_quasi"]`
  = max deflection of quasi-permanent (+ G-only) results after the envelope pass.
  `nachweis_ec5.py` uses this as the kdef base: `delta_end = (1+kdef) * delta_quasi`.
  Fallback to `delta_inst` for old snapshots without that key (conservative).

**2 – Governing span for L/n limit: first key → max feld_***
- Old: `next(iter(spannweiten.values()))` could return any span including kragarm
- Fix: `max(v for k,v in spannweiten.items() if k.startswith("feld_"))`

**3 – Schnell-Modus bug: `kdef` → `(1+kdef)` for delta_end**
- Old: `delta_end = kdef * delta_inst` → delta_end < delta_inst (physically impossible)
- Fix: `delta_end = (1 + kdef) * delta_inst`

### kdef in the database
- `datenbank_holz.py` stores kdef per `(Typ, NKL)` key → correctly differentiated
  by material type AND service class (NKL 1/2/3). Values from EC5 Table 3.2.

## Auflagerkräfte (Support Reactions) – 2026-03-08

### Where reactions are computed
- `feebb_schnittstelle_ec.py` FeebbBerechnungEC class, called in `_erstelle_envelopes()`
- `_get_auflager_knoten()` – nodes with `supports[k][0] == -1`
- `_extrahiere_reaktionen_aus_querkraft()` – shear-jump method, NPTS_STRIDE=19
- `_berechne_auflagerkraefte()` → `system_memory["Auflagerkraefte"]`
- API route reads `result.get("Auflagerkraefte")` → `CalculationResponse.auflagerkraefte`
- Frontend: `AuflagerKraefte` interface in `types/beam.ts`, `AuflagerTable.tsx` component

### Critical: felder["laenge"] is in METRES, NOT mm
- `feld["laenge"]` comes directly from spannweiten [m]
- `l_element = laenge * 1000 / n_elemente` confirms this (internal FEM uses mm)
- For x-position of supports: just sum `feld["laenge"]` directly (no /1000 needed)

### NPTS_STRIDE = 19 (not 20)
- Postprocessor uses 20 pts/element with `pop(-1)` dedup on shared nodes
- Total array length = n_elements * 19 + 1
- Node k → array index k * 19

### GZG typ values: "charakteristisch", "haeufig", "quasi_staendig", "nur_g"
- For reactions, filter: {"charakteristisch", "nur_g"} (nur_g = fallback when no live loads)

## stark-tools Integration
- stark-nginx + stark-auth managed by stark-tools docker-compose (external network)
- stark-statik runs independently via its own deploy.yml
- NEVER add stark-statik to stark-tools docker-compose.yml
- See stark-tools MEMORY.md for portal architecture details
