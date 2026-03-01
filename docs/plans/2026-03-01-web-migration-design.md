# Statik-Tool Web-Migration: Detailed Design

**Date**: 2026-03-01
**Status**: Draft - Pending Approval
**Tech Stack**: FastAPI (Python) + React (TypeScript) + Tailwind CSS
**Target**: Integration in stark-tools portal (tools.askbenstark.com)

---

## 1. Repository & Project Structure

```
Durchlaufträger/
├── backend/                          # UNCHANGED - existing calculation engine
│   ├── calculations/                 # FEM, load combos, EC5 checks
│   ├── database/                     # Timber material DB
│   ├── project/                      # Project/Position management
│   └── service/                      # Orchestration, validation
│
├── web/                              # NEW - Web application
│   ├── api/                          # FastAPI backend (thin wrapper)
│   │   ├── main.py                   # FastAPI app, CORS, lifespan
│   │   ├── deps.py                   # Dependencies (DB, ProjectManager, auth)
│   │   ├── routes/
│   │   │   ├── calculation.py        # POST /api/calculate
│   │   │   ├── projects.py           # CRUD /api/projects
│   │   │   ├── positions.py          # CRUD /api/projects/{id}/positions
│   │   │   └── materials.py          # GET /api/materials (DB queries)
│   │   └── schemas/
│   │       ├── calculation.py        # Pydantic: CalculationRequest/Response
│   │       ├── project.py            # Pydantic: Project, Position models
│   │       └── material.py           # Pydantic: Material, Kmod, SiBeiwerte
│   │
│   └── frontend/                     # React SPA
│       ├── src/
│       │   ├── App.tsx               # Root: routing, theme, auth
│       │   ├── main.tsx              # Entry point
│       │   ├── components/           # Shared UI components
│       │   │   ├── ui/               # Shadcn/ui primitives
│       │   │   ├── Layout.tsx        # Sidebar + Main content shell
│       │   │   ├── ThemeToggle.tsx    # Dark/Light mode switch
│       │   │   └── KaTeXFormula.tsx   # LaTeX rendering component
│       │   ├── modules/              # Calculation modules (plugin-like)
│       │   │   └── durchlauftraeger/
│       │   │       ├── index.tsx             # Module registration
│       │   │       ├── DurchlauftraegerModule.tsx  # Main module container
│       │   │       ├── InputPanel.tsx         # Left: all input sections
│       │   │       ├── ResultsPanel.tsx       # Right: all output sections
│       │   │       ├── inputs/
│       │   │       │   ├── CalculationMode.tsx
│       │   │       │   ├── SystemInput.tsx
│       │   │       │   ├── LoadInput.tsx
│       │   │       │   ├── CrossSectionInput.tsx
│       │   │       │   └── ServiceabilityInput.tsx
│       │   │       ├── results/
│       │   │       │   ├── SystemDiagram.tsx       # SVG beam visualization
│       │   │       │   ├── LoadCombinations.tsx     # KaTeX formulas
│       │   │       │   ├── DesignLoad.tsx           # KaTeX Ed formula
│       │   │       │   ├── BendingVerification.tsx  # KaTeX bending check
│       │   │       │   ├── ShearVerification.tsx    # KaTeX shear check
│       │   │       │   ├── DeflectionVerification.tsx # KaTeX deflection
│       │   │       │   ├── SectionForcesTable.tsx   # Max M, V values
│       │   │       │   └── ForcesDiagram.tsx        # Plotly M/Q/w plots
│       │   │       └── hooks/
│       │   │           ├── useCalculation.ts   # API call + debounce
│       │   │           └── useModuleState.ts   # Form state management
│       │   ├── features/
│       │   │   ├── projects/         # Project Explorer
│       │   │   │   ├── ProjectExplorer.tsx
│       │   │   │   ├── ProjectTree.tsx
│       │   │   │   ├── NewProjectDialog.tsx
│       │   │   │   └── hooks/useProjects.ts
│       │   │   ├── positions/        # Position Tabs
│       │   │   │   ├── PositionTabs.tsx
│       │   │   │   └── hooks/usePositions.ts
│       │   │   └── welcome/          # Welcome page
│       │   │       └── WelcomePage.tsx
│       │   ├── hooks/                # Global hooks
│       │   │   ├── useTheme.ts
│       │   │   └── useAuth.ts
│       │   ├── lib/                  # Utilities
│       │   │   ├── api.ts            # Fetch wrapper
│       │   │   └── constants.ts      # URLs, config
│       │   └── types/                # TypeScript interfaces
│       │       ├── calculation.ts    # Snapshot, results types
│       │       ├── project.ts        # Project, Position types
│       │       └── material.ts       # Material DB types
│       ├── index.html
│       ├── package.json
│       ├── tsconfig.json
│       ├── tailwind.config.ts
│       └── vite.config.ts
│
├── Dockerfile                        # Multi-stage: build React + serve with FastAPI
├── docker-compose.yml                # Local development (hot-reload)
├── docker-compose.prod.yml           # Production build
├── requirements.txt                  # Python dependencies
├── main_v2.py                        # KEEP - legacy desktop app
├── frontend/                         # KEEP - legacy CustomTkinter (untouched)
└── Projekte/                         # User project data
```

---

## 2. API Design (FastAPI)

### 2.1 Calculation Endpoints

```
POST /api/calculate
  Body: CalculationRequest (full snapshot)
  Response: CalculationResponse (results + LaTeX)
  Notes: Synchronous - wraps OrchestratorService with asyncio
         Timeout: 30s
         Returns validation errors as 422

POST /api/calculate/deflection-only
  Body: DeflectionCheckRequest (snapshot with existing results)
  Response: DeflectionCheckResponse (updated EC5 checks only)
  Notes: Fast path - only recalculates EC5 when cross-section changes
```

### 2.2 Material Database Endpoints

```
GET /api/materials/groups
  Response: ["Balken", "BSH", ...]

GET /api/materials/types?gruppe=Balken
  Response: ["Nadelholz", "Laubholz"]

GET /api/materials/strength-classes?gruppe=Balken&typ=Nadelholz
  Response: ["C14", "C16", "C18", "C24", ...]

GET /api/materials/properties?gruppe=Balken&typ=Nadelholz&klasse=C24&nkl=1
  Response: { fmyk, fvk, E, roh_mean, gamma_m, kdef }

GET /api/materials/load-categories
  Response: [{ kategorie, lastfall, psi0, psi1, psi2, kled }, ...]

GET /api/materials/load-types
  Response: ["g", "s", "w", "p", ...]

GET /api/materials/categories-for-load?lastfall=s
  Response: ["Schneelast Kat. H", "Schneelast >1000m", ...]
```

### 2.3 Project Management Endpoints

```
GET    /api/projects                              → List user's projects
POST   /api/projects                              → Create project
GET    /api/projects/{project_id}                  → Get project metadata
PUT    /api/projects/{project_id}                  → Update project
DELETE /api/projects/{project_id}                  → Delete project
POST   /api/projects/{project_id}/share            → Share with other user

GET    /api/projects/{id}/positions                → List positions
POST   /api/projects/{id}/positions                → Create position
GET    /api/projects/{id}/positions/{pos_id}        → Get position data
PUT    /api/projects/{id}/positions/{pos_id}        → Save position
DELETE /api/projects/{id}/positions/{pos_id}        → Delete position

GET    /api/projects/{id}/folders                   → List folders
POST   /api/projects/{id}/folders                   → Create folder
PUT    /api/projects/{id}/positions/{pos_id}/move    → Move to folder
```

### 2.4 Auth Endpoint

```
GET /api/auth/me
  Response: { username, role }
  Notes: Reads stark_session cookie, validates with auth service
         Returns 401 if not authenticated
```

### 2.5 Data Schemas (Pydantic)

```python
# CalculationRequest - mirrors existing snapshot format
class CalculationRequest(BaseModel):
    sprungmass: float = 1.0
    berechnungsmodus: BerechnungsmodusSchema
    spannweiten: Dict[str, float]       # {"kragarm_links": 0, "feld_1": 5.0, ...}
    lasten: List[LastSchema]
    querschnitt: QuerschnittSchema
    gebrauchstauglichkeit: GebrauchstauglichkeitSchema

class LastSchema(BaseModel):
    lastfall: str                        # "g", "s", "w", "p"
    wert: float                          # kN/m²
    kategorie: str                       # "Eigengewicht", "Schneelast Kat. H"
    kommentar: str = ""
    nkl: int = 1                         # 1, 2, 3
    eigengewicht: bool = False

class QuerschnittSchema(BaseModel):
    breite_qs: float                     # mm
    hoehe_qs: float                      # mm
    materialgruppe: str                  # "Balken"
    typ: str                             # "Nadelholz"
    festigkeitsklasse: str               # "C24"

class GebrauchstauglichkeitSchema(BaseModel):
    situation: str = "Allgemein"
    w_c: float = 0.0                     # mm
    w_inst_grenz: float = 300            # L/x
    w_fin_grenz: float = 200
    w_net_fin_grenz: float = 300

# CalculationResponse
class CalculationResponse(BaseModel):
    lastfallkombinationen: Dict[str, LastkombiResult]
    gzg_lastfallkombinationen: Dict[str, GzgKombiResult]
    schnittgroessen: SchnittgroessenResult
    ec5_nachweise: EC5NachweiseResult
    errors: List[str] = []
```

---

## 3. Frontend Architecture (React)

### 3.1 Tech Stack Details

| Technology | Purpose | Version |
|---|---|---|
| React | UI Framework | 19.x |
| TypeScript | Type Safety | 5.x |
| Vite | Build Tool | 6.x |
| Tailwind CSS | Styling | 4.x |
| shadcn/ui | UI Components | latest |
| KaTeX | LaTeX Rendering | 0.16.x |
| Plotly.js | Interactive Diagrams | 2.x |
| Zustand | State Management | 5.x |
| React Query (TanStack) | API State | 5.x |

### 3.2 Component Hierarchy

```
App
├── ThemeProvider (dark/light via Tailwind class strategy)
├── QueryClientProvider (React Query)
└── Layout
    ├── Sidebar (resizable, collapsible)
    │   ├── ProjectExplorer
    │   │   ├── ProjectTree (recursive, collapsible nodes)
    │   │   ├── ContextMenu (right-click: rename, delete, duplicate, move)
    │   │   └── NewPositionButton
    │   └── ResizeHandle
    └── MainContent
        ├── WelcomePage (when no position open)
        │   ├── NewProjectButton
        │   ├── OpenProjectButton
        │   └── RecentProjectsList
        └── PositionTabs (tab bar + content)
            └── PositionTab
                └── ModuleTabs (sub-tabs per module)
                    └── DurchlauftraegerModule
                        ├── InputPanel (left, scrollable)
                        │   ├── CalculationMode
                        │   ├── SystemInput
                        │   ├── LoadInput
                        │   ├── NklEigengewichtSection
                        │   ├── SectionForcesDisplay
                        │   ├── CrossSectionInput
                        │   └── ServiceabilityInput
                        └── ResultsPanel (right, scrollable)
                            ├── SystemDiagram
                            ├── LoadCombinations
                            ├── DesignLoad
                            ├── BendingVerification
                            ├── ShearVerification
                            ├── DeflectionVerification
                            └── ForcesDiagramButton → ForcesDiagramModal
```

### 3.3 State Management

**Zustand Store** for module state:
```typescript
interface DurchlauftraegerState {
  // Input state
  berechnungsmodus: { ec_modus: boolean }
  sprungmass: number
  spannweiten: Record<string, number>
  feldanzahl: number
  kragarmLinks: boolean
  kragarmRechts: boolean
  lasten: LastInput[]
  nkl: number
  eigengewichtAktiv: boolean
  querschnitt: QuerschnittInput
  gebrauchstauglichkeit: GebrauchstauglichkeitInput
  selectedVariant: 1 | 2 | 3
  anzeigeModus: 'massgebend' | 'alle'

  // Results state
  results: CalculationResponse | null
  isCalculating: boolean
  errors: string[]

  // Actions
  setField: (field: string, value: any) => void
  addLast: () => void
  removeLast: (index: number) => void
  setResults: (results: CalculationResponse) => void
}
```

**React Query** for server state:
- `useProjects()` - Project list with cache
- `useMaterials()` - Material DB (cached, rarely changes)
- `useCalculation()` - Mutation for calculations with debounce

### 3.4 Calculation Flow (Debounced)

```
User types/selects → Zustand state updates →
  useEffect detects change → 500ms debounce →
    POST /api/calculate (React Query mutation) →
      Loading spinner shown →
        Results arrive → Zustand store updated →
          ResultsPanel re-renders:
            - KaTeX formulas update
            - SVG system diagram updates
            - Plotly diagrams update (if open)
```

---

## 4. Input Form Field Mapping

### 4.1 Berechnungsmodus (Calculation Mode)

| Current Widget | Web Component | Behavior |
|---|---|---|
| `CTkRadioButton` "⚡ Volllast (schnell)" | Radio button group | `ec_modus: false` |
| `CTkRadioButton` "🔬 EC-Kombinatorik" | Radio button group | `ec_modus: true` |

### 4.2 Systemeingabe (System Input)

| Current Widget | Web Component | Behavior |
|---|---|---|
| `sprungmass_entry` (CTkEntry, "1.00") | Number input, step=0.01, suffix "m" | Float, comma→dot |
| `feldanzahl_var` (IntVar, 1) | Stepper: [-] [1] [+], range 1-5 | Dynamic span fields |
| `kragarm_links` (BooleanVar) | Checkbox "Kragarm links" | Shows/hides cantilever field |
| `kragarm_rechts` (BooleanVar) | Checkbox "Kragarm rechts" | Shows/hides cantilever field |
| `spannweiten_eingaben[]` (dynamic CTkEntry) | Dynamic number inputs per field | "Feld 1 [m]", "Feld 2 [m]" etc. |

### 4.3 Lasten (Loads) - Dynamic Table

| Current Widget | Web Component | Behavior |
|---|---|---|
| `lf_combo` (CTkComboBox) | Select dropdown | Load type: g, s, w, p |
| `wert` (CTkEntry) | Number input, step=0.01 | kN/m², comma→dot |
| `detail_combo` (CTkComboBox) | Select dropdown (filtered by load type) | Category from DB |
| `kommentar` (CTkEntry) | Text input | Free text |
| `remove` button | "×" icon button | Remove row |
| `plus_button` | "+ Neue Last" button | Add row (max 5) |

### 4.4 NKL & Eigengewicht

| Current Widget | Web Component | Behavior |
|---|---|---|
| `nkl_dropdown` ("NKL 1/2/3") | Select dropdown | Service class |
| `eigengewicht_checkbutton` | Checkbox | Self-weight active |
| `radio_lastkombi_1/2` | Toggle: "Maßgebend" / "Alle" | Display filter |

### 4.5 Schnittgrößen (Display Only)

| Current Widget | Web Component |
|---|---|
| `max_moment_kalt` label | Styled output: "My,d: 31.4 kNm" |
| `max_querkraft_kalt` label | Styled output: "Vz,d: 24.8 kN" |
| `schnittgroeßen_anzeige_button` checkbox | Button: "📊 Schnittkraftverläufe" → opens modal |

### 4.6 Bemessungsquerschnitt (Cross-Section)

| Current Widget | Web Component | Behavior |
|---|---|---|
| `materialgruppe_var_1` (CTkComboBox) | Select: "Balken", "BSH" | Cascading: updates type options |
| `querschnitt_var_1/2/3` (CTkComboBox) | 3× Select: "Nadelholz", "Laubholz" | Per variant |
| `festigkeitsklasse_var_1/2/3` (CTkComboBox) | 3× Select: "C14"..."C50" | Cascading from type |
| `radiobox_var` (IntVar, 1-3) | Radio group: "Variante 1/2/3" | Selects active variant |
| `b_entry_1/2/3` (CTkEntry) | 3× Number input, suffix "mm" | Width per variant |
| `h_entry_1/2/3` (CTkEntry) | 3× Number input, suffix "mm" | Height per variant |

**Web Layout**: 3-column grid for variants, with radio selector above dimensions.

### 4.7 Gebrauchstauglichkeit (Serviceability)

| Current Widget | Web Component | Behavior |
|---|---|---|
| `situation_var` (CTkComboBox) | Select: "Allgemein", "Überhöhte...", "Eigene Werte" | Changes limit display |
| `w_c_überhoehung` (CTkEntry) | Number input, suffix "mm" | Camber value |
| Limit labels (Allgemein) | Static display: "w_inst: L/300" | Read-only for presets |
| `w_inst_eigen` / `w_fin_eigen` / `w_net_fin_eigen` | Number inputs (only for "Eigene Werte") | Custom limits |

**Preset Values**:
- Allgemein: w_inst=L/300, w_fin=L/200, w_net=L/300
- Überhöhte: w_inst=L/200, w_fin=L/150, w_net=L/250
- Eigene: User-defined

---

## 5. Output/Display Component Mapping

### 5.1 System Diagram (SVG)

**Current**: Matplotlib figure → PNG → CTkLabel
**New**: React SVG component (no external library needed)

- Beam: `<line>` element, normalized to container width
- Supports: `<polygon>` triangles + `<line>` bases
- Labels: `<text>` elements (A, B, C...)
- Dimensions: `<line>` arrows + `<text>` span values
- Field labels: `<text>` "Feld 1", "Feld 2"
- Theme: CSS classes for dark/light colors
- Responsive: viewBox scaling

### 5.2 Load Combinations (KaTeX)

**Current**: LaTeX string → Matplotlib render → PNG → CTkLabel
**New**: LaTeX string → KaTeX inline render in `<div>`

```tsx
<KaTeXFormula latex={kombi.latex} />
// Uses: katex.renderToString(latex, { displayMode: true })
```

- Governing combination: highlighted border/background
- Design load (Ed): separate section below
- Toggle: "Maßgebend" shows only governing, "Alle" shows all

### 5.3 EC5 Verification (KaTeX)

**Current**: LaTeX string → Matplotlib render → PNG → CTkLabel
**New**: KaTeX with pass/fail styling

```tsx
<VerificationBlock
  title="Biegungsnachweis"
  latex={nachweise.biegung.latex}
  passed={nachweise.biegung.erfuellt}
  utilization={nachweise.biegung.ausnutzung}
/>
```

- ✅ Pass: Green accent border
- ❌ Fail: Red accent border
- Utilization bar: visual percentage indicator

### 5.4 Internal Forces Diagram (Plotly.js)

**Current**: Matplotlib in separate CTkToplevel window
**New**: Plotly.js in modal dialog (or expandable section)

4 subplots:
1. **System sketch** (simplified SVG, reused from 5.1)
2. **Moment diagram** (red, kNm, inverted y-axis)
3. **Shear diagram** (blue, kN, inverted y-axis)
4. **Deflection diagram** (purple, mm, inverted y-axis)

**Plotly advantages over Matplotlib**:
- Hover: Shows exact values at cursor position
- Zoom: Click-drag to zoom into sections
- Pan: Move along beam
- Export: Built-in "Download as PNG" button
- Load pattern shading: Plotly shapes for green/red field backgrounds
- Extrema annotations: Plotly annotations with arrows

---

## 6. Authentication & stark-tools Integration

### 6.1 Auth Flow

```
Browser → nginx (/statik/) →
  auth_request /internal/auth →
    stark-auth validates stark_session cookie →
      200 OK → nginx proxies to FastAPI
      401    → redirect to /login?next=/statik/
```

### 6.2 nginx Location Block

```nginx
location /statik/ {
    auth_request /internal/auth;
    error_page 401 = @login_redirect;
    set $upstream statik;
    proxy_pass http://$upstream:8000;    # FastAPI on port 8000
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}
```

### 6.3 Portal Tile (auth/app.py KACHELN)

```python
{
    "icon": "📐",
    "titel": "Durchlaufträger – EC5",
    "beschreibung": "Berechnung und Bemessung von Durchlaufträgern im Holzbau nach EC5.",
    "url": "/statik/",
    "link_text": "Öffnen →",
    "rollen": ["admin", "felix"],  # Admin + Felix
    "css_extra": "",
},
```

### 6.4 User Identification

FastAPI reads `stark_session` cookie → validates against auth service:
- Each user gets their own project directory: `Projekte/{username}/`
- Shared projects in `Projekte/_shared/`

---

## 7. Project Storage & Sharing

### 7.1 Directory Structure (Server)

```
/data/projekte/
├── admin/                    # Admin's private projects
│   ├── Demo_Wohnhaus/
│   │   ├── project.json
│   │   └── EG/
│   │       └── Position_1_01.json
│   └── Neubau_Mueller/
│       └── ...
├── felix_k/                  # Felix's private projects
│   └── ...
└── _shared/                  # Shared projects
    └── Gemeinschaftsprojekt/
        └── ...
```

### 7.2 Sharing Mechanism

- Default: Project is private (in user's directory)
- Share action: Copies/moves project to `_shared/` and adds access metadata
- Both users can see and edit shared projects
- Future: Per-position locking to prevent conflicts

---

## 8. Docker & Deployment

### 8.1 Dockerfile (Multi-stage)

```dockerfile
# Stage 1: Build React frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

# Stage 2: Python backend + serve built frontend
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY web/api/ ./web/api/
COPY --from=frontend-build /app/frontend/dist ./web/frontend/dist
EXPOSE 8000
CMD ["uvicorn", "web.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 docker-compose.yml (Development)

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app/backend
      - ./web/api:/app/web/api
      - ./Projekte:/data/projekte
    environment:
      - PROJEKTE_ROOT=/data/projekte
    command: uvicorn web.api.main:app --reload --host 0.0.0.0 --port 8000

  frontend:
    image: node:22-alpine
    working_dir: /app
    ports:
      - "5173:5173"
    volumes:
      - ./web/frontend:/app
    command: npm run dev -- --host
    environment:
      - VITE_API_URL=http://localhost:8000
```

### 8.3 stark-tools docker-compose.yml Addition

```yaml
statik:
  build:
    context: /root/statikprogramm
    dockerfile: Dockerfile
  restart: unless-stopped
  volumes:
    - /data/statik-projekte:/data/projekte
  environment:
    - PROJEKTE_ROOT=/data/projekte
    - AUTH_SERVICE_URL=http://stark-auth:5000
```

### 8.4 Local Development (ohne Docker)

```bash
# Terminal 1: Backend
cd Durchlaufträger
pip install -r requirements.txt
uvicorn web.api.main:app --reload --port 8000

# Terminal 2: Frontend
cd Durchlaufträger/web/frontend
npm install
npm run dev
```

Opens at http://localhost:5173 with API proxy to :8000

---

## 9. Theme System (Dark/Light)

### Tailwind CSS class strategy:

```html
<html class="dark"> <!-- or remove for light -->
```

### Color Tokens (CSS variables):

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --bg-input: #ffffff;
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --accent-blue: #2563eb;
  --accent-green: #16a34a;
  --accent-red: #dc2626;
  --border: #e5e7eb;
}

.dark {
  --bg-primary: #1e1e1e;
  --bg-secondary: #2d2d2d;
  --bg-input: #3c3c3c;
  --text-primary: #dce4ee;
  --text-secondary: #9ca3af;
  --accent-blue: #60a5fa;
  --accent-green: #4ade80;
  --accent-red: #f87171;
  --border: #404040;
}
```

### KaTeX Theme Integration:
- KaTeX renders in text color by default
- CSS: `.katex { color: var(--text-primary); }`

### Plotly Theme Integration:
- Layout colors from CSS variables via JS
- `paper_bgcolor: 'transparent'`
- `plot_bgcolor: 'transparent'`
- Grid/axis colors from theme

---

## 10. Module Registration System

### Backend Module Interface:

Each module (Durchlaufträger, future Brandschutz, Stahlbau) implements:

```python
class ModuleInterface(ABC):
    @abstractmethod
    def get_module_id(self) -> str: ...
    @abstractmethod
    def get_display_name(self) -> str: ...
    @abstractmethod
    def calculate(self, snapshot: dict) -> dict: ...
    @abstractmethod
    def validate(self, snapshot: dict) -> list[str]: ...
```

### Frontend Module Interface:

```typescript
interface CalculationModule {
  id: string                           // "durchlauftraeger"
  displayName: string                  // "Durchlaufträger"
  icon: string                         // "📐"
  InputPanel: React.FC<InputPanelProps>
  ResultsPanel: React.FC<ResultsPanelProps>
  defaultState: () => ModuleState
  getApiEndpoint: () => string         // "/api/calculate"
}
```

New modules register via:
```typescript
// modules/registry.ts
export const MODULE_REGISTRY: CalculationModule[] = [
  durchlauftraegerModule,
  // brandschutzModule,  // future
  // stahlbauModule,     // future
]
```

---

## 11. Migration Checklist: Feature Parity

Every feature from the current desktop app must be present in the web version:

### Input Features
- [ ] Calculation mode toggle (Volllast / EC-Kombinatorik)
- [ ] Sprungmaß input
- [ ] Field count selector (1-5) with +/- buttons
- [ ] Cantilever toggles (left/right)
- [ ] Dynamic span length inputs
- [ ] Dynamic load table (1-5 rows) with add/remove
- [ ] Load type dropdown (from DB)
- [ ] Load category dropdown (cascading from type, from DB)
- [ ] Load value input
- [ ] Load comment input
- [ ] NKL dropdown (1/2/3)
- [ ] Self-weight checkbox
- [ ] Display mode toggle (governing / all combinations)
- [ ] Material group dropdown
- [ ] 3 variants: Type, Strength class, Width, Height
- [ ] Variant selection radio buttons
- [ ] Serviceability situation selector
- [ ] Custom deflection limits (for "Eigene Werte")
- [ ] Camber (w_c) input

### Output Features
- [ ] System diagram (beam + supports + spans + labels)
- [ ] Load combination formulas (LaTeX)
- [ ] Design load formula (LaTeX)
- [ ] Bending verification formula (LaTeX) with pass/fail
- [ ] Shear verification formula (LaTeX) with pass/fail
- [ ] Deflection verification formulas (3x, LaTeX) with pass/fail
- [ ] Section forces values (My,d, Vz,d)
- [ ] Internal forces diagrams (M, Q, w)
- [ ] Load pattern visualization in diagrams
- [ ] Extrema annotations in diagrams

### Project Management Features
- [ ] Project explorer tree
- [ ] Create/Open/Save project
- [ ] Create/Rename/Delete positions
- [ ] Folder organization
- [ ] Position tabs (multiple open)
- [ ] Auto-save

### UI Features
- [ ] Dark/Light mode toggle
- [ ] Responsive layout
- [ ] Loading indicator during calculation

### New Features (Web-only)
- [ ] Multi-user access (admin + felix_k)
- [ ] Project sharing
- [ ] Interactive diagrams (hover, zoom)
- [ ] Sharper formula rendering (KaTeX vs Matplotlib)
- [ ] URL-based routing (bookmarkable positions)
- [ ] PDF export (future phase)

---

## 12. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- FastAPI project setup with existing backend integration
- React project setup (Vite + Tailwind + shadcn/ui)
- API schemas (Pydantic models matching existing snapshot format)
- `/api/calculate` endpoint wrapping OrchestratorService
- `/api/materials/*` endpoints wrapping datenbank_holz
- Basic React layout (sidebar + main content)
- Theme system (dark/light)

### Phase 2: Input Form (Week 3-4)
- All input components (mapped 1:1 from eingabemaske.py)
- Form state management (Zustand)
- Debounced calculation trigger
- API integration (React Query)
- Loading states

### Phase 3: Results Display (Week 4-5)
- KaTeX formula rendering
- System diagram (SVG)
- Verification displays (bending, shear, deflection)
- Load combination display
- Section forces table

### Phase 4: Diagrams (Week 5-6)
- Plotly.js integration
- Moment diagram
- Shear diagram
- Deflection diagram
- Load pattern shading
- Extrema annotations

### Phase 5: Project Management (Week 6-7)
- Project CRUD API
- Project explorer component
- Position tabs
- Auto-save
- Welcome page

### Phase 6: Integration & Polish (Week 8)
- Docker setup
- stark-tools integration (nginx, auth, portal tile)
- User-specific project directories
- Project sharing
- Testing against desktop app
- Bug fixes

### Phase 7: PDF Export (Future)
- Report generator
- Include: inputs, system, combinations, verifications, diagrams
- Professional layout

---

## 13. Testing Strategy

### Backend API Tests
- Validate Pydantic schemas against existing snapshot format
- Compare API calculation results with desktop app results
- Test all material DB queries
- Test project CRUD operations

### Frontend Tests
- Component tests for each input section
- Integration test: full calculation flow
- Visual regression: compare with desktop screenshots
- Cross-browser: Chrome, Firefox, Safari

### Verification Tests (SAFETY-CRITICAL)
- Reference calculations: Compare web results with desktop app for same input
- Edge cases: Single span, 5 spans, cantilevers, extreme loads
- Unit consistency: Verify kN/mm/m conversions
- Norm values: Cross-check kmod, gamma_M, psi factors
