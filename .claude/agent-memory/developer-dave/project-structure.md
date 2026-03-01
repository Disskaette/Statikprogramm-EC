# Project Structure Details

## Migration Decisions (2026-03-01)
- **Stack**: FastAPI + React + TypeScript + Tailwind CSS + shadcn/ui
- **Formulas**: KaTeX in browser
- **Diagrams**: Plotly.js (interactive)
- **System Viz**: SVG components
- **State**: Zustand + React Query (TanStack)
- **Deployment**: Docker multi-stage, integrated into stark-tools
- **Access**: admin + felix_k roles

## Web App Location
- New code lives in `web/` directory
- `web/api/` - FastAPI backend (thin wrapper around existing backend)
- `web/frontend/` - React SPA
- Existing `backend/` and `frontend/` stay UNTOUCHED

## API Design
- POST /api/calculate - wraps OrchestratorService
- GET /api/materials/* - wraps datenbank_holz
- CRUD /api/projects/* - wraps ProjectManager
- GET /api/auth/me - session validation

## Input Form: 32 elements mapped 1:1
- See design doc: docs/plans/2026-03-01-web-migration-design.md

## Module System
- Frontend: MODULE_REGISTRY array with CalculationModule interface
- Backend: ModuleInterface ABC
- Extensible for Stahlbau, Brandschutz, Auflagerpressung
