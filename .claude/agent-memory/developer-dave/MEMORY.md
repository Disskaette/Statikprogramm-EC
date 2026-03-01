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
- `web/api/routes/projects.py` – CRUD projects + positions
- `web/frontend/src/` – React app
- See [web-layer.md](web-layer.md) for full API + React component details

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

## stark-tools Integration
- stark-nginx + stark-auth managed by stark-tools docker-compose (external network)
- stark-statik runs independently via its own deploy.yml
- NEVER add stark-statik to stark-tools docker-compose.yml
- See stark-tools MEMORY.md for portal architecture details
