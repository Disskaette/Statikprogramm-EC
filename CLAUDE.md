# CLAUDE.md – Statikprogramm-EC (Durchlaufträger)

Dieses Repo enthält das Durchlaufträger-Statik-Tool: FastAPI-Backend (EC5-Berechnung via FEEBB)
+ React-Frontend (Vite). Es ist eingebunden ins stark-tools Portal unter
https://tools.askbenstark.com/statik/

## Deployment-Architektur (NICHT ÄNDERN ohne Absprache)

### Wie das Tool deployed wird

**Trigger:** Jeder Push auf `main` triggert `.github/workflows/deploy.yml`.

Der Workflow:
1. SSH auf den VPS (Hetzner)
2. Repo nach `/root/statikprogramm/` clonen / pullen
3. Docker Image bauen (Multi-Stage: Node für Vite-Build, Python für Runtime)
4. Container `stark-statik` stoppen, entfernen, neu starten
5. Container joinet das `stark-tools` Docker-Netzwerk

**Das Tool ist KEIN Teil von stark-tools docker-compose.yml.**
Es läuft als eigenständiger `docker run` Container.

### Sub-Path-Routing (/statik/)

Das Tool läuft unter dem Pfad `/statik/` im Portal. Dafür sind folgende Dinge abgestimmt:

```
nginx (stark-tools):
  location /statik/ {
    proxy_pass http://stark-statik:8000/;  ← trailing slash: strippt /statik/
  }

Dockerfile (Build-Args):
  VITE_BASE_URL=/statik/    → Vite baut Assets als /statik/assets/...
  VITE_API_BASE_URL=/statik → React ruft /statik/api/... auf

FastAPI empfängt:   /         (SPA)
                    /assets/* (JS/CSS)
                    /api/*    (Backend)
```

**NIEMALS** diese Build-Args entfernen oder `VITE_BASE_URL` auf `/` setzen –
dann werden Assets nicht gefunden und das Tool zeigt einen weißen Bildschirm.

### Persistente Daten

Projekte werden auf dem VPS gespeichert:
- VPS-Pfad: `/root/statikprogramm/Projekte/`
- Container-Pfad: `/app/Projekte/`
- Volume-Mount: `-v /root/statikprogramm/Projekte:/app/Projekte:rw`

**NIEMALS** den Container-Pfad für Projekte ändern ohne Volume-Anpassung.

### Benötigte GitHub Secrets (Settings → Secrets → Actions)

| Secret | Inhalt |
|---|---|
| `SSH_HOST` | VPS IP-Adresse |
| `SSH_USER` | SSH-Benutzername (z.B. `root`) |
| `SSH_KEY` | Privater SSH-Schlüssel |

`GITHUB_TOKEN` ist automatisch verfügbar (von GitHub Actions).

## Projektstruktur (Kurzübersicht)

```
backend/              – Python-Berechnungslogik (EC0/EC1/EC5, FEEBB-FEM)
  calculations/       – FEM-Solver, Schnittkräfte, EC5-Nachweise, Lastkombinationen
  database/           – Holzwerkstoff-Datenbank (kmod, Festigkeitsklassen, ψ-Werte)
  service/            – OrchestratorService, ValidationService
  project/            – ProjectManager, PositionModel

web/                  – Web-Layer (NICHT die Berechnungslogik!)
  api/                – FastAPI-Routes (/api/calculate, /api/materials, /api/projects)
  frontend/           – React + Vite + TypeScript + TailwindCSS
    src/
      components/     – UI-Komponenten (input/, results/, sidebar/, ui/)
      stores/         – Zustand-Store (useBeamStore, useProjectStore)
      hooks/          – React Query Hooks (useMaterials, useCalculation, useProjects)
      types/          – TypeScript-Interfaces (beam.ts, project.ts)

Dockerfile            – Multi-Stage: node:22-alpine (Vite) → python:3.12-slim (Runtime)
requirements-web.txt  – Python-Dependencies für die Web-API
```

## Kritische Regeln für Backend-Änderungen

**Die Berechnungslogik in `backend/` ist sicherheitsrelevant (Statik!).**

- **Nie** `backend/calculations/`, `backend/database/`, `backend/service/` ändern
  ohne explizite Freigabe durch den Nutzer.
- Normenwerte (kmod, gamma_M, f_md, ψ-Werte) sind durch Eurocode festgelegt –
  **niemals raten, immer nachfragen.**
- Einheiten: Momente in [Nmm], Kräfte in [N], Durchbiegungen in [mm] intern.
  Anzeige im Frontend: kNm, kN, mm.

## Bekannte Fallstricke

- `feebb_schnittstelle.py` importiert tkinter/matplotlib – im Web-Container werden
  diese durch No-Op-Stubs ersetzt (`web/api/deps.py::_install_tkinter_stubs()`)
- Python 3.12+ erforderlich (f-String mit Backslash in `nachweis_ec5.py` Zeile 288)
- `snapshot['wert']` muss STRING sein, `snapshot['sprungmass']` kann FLOAT sein
- Load-Kategorien müssen exakt mit DB-Werten übereinstimmen
