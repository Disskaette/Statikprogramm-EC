# Phase 2: Input Form – Implementation Plan

**Goal:** Build the complete input form (Eingabemaske) for the Durchlaufträger web app, matching all 32+ fields from the desktop GUI.

**Architecture:** Zustand store holds all form state. React components are organized by section. Material DB data is fetched via React Query and cached. Form changes trigger debounced API calls. The form produces a `CalculationRequest` JSON matching the API schema.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, Zustand, TanStack React Query

---

## Component Structure

```
src/
├── stores/
│   └── useBeamStore.ts          — Zustand store (all form + result state)
├── types/
│   └── beam.ts                  — TypeScript interfaces for form data
├── hooks/
│   ├── useTheme.ts              — (existing)
│   ├── useMaterials.ts          — React Query hooks for material DB
│   └── useCalculation.ts        — React Query mutation for /api/calculate
├── components/
│   ├── layout/                  — (existing: Layout, ThemeToggle)
│   └── input/
│       ├── InputForm.tsx         — Main form container (orchestrates sections)
│       ├── SystemSection.tsx     — Sprungmaß, spans, cantilevers
│       ├── LoadsSection.tsx      — Dynamic load table (add/remove rows)
│       ├── LoadRow.tsx           — Single load row (lastfall, wert, kategorie, kommentar)
│       ├── CrossSectionSection.tsx — 3 variants, material cascading
│       ├── DeflectionSection.tsx — Presets + custom limits
│       └── CalculationModeToggle.tsx — EC vs Quick mode
```

---

### Task 1: TypeScript types and Zustand store

Create `src/types/beam.ts` with interfaces matching the API schema, and `src/stores/useBeamStore.ts` with all form state, actions, and computed `toCalculationRequest()`.

### Task 2: React Query hooks for materials and calculation

Create `src/hooks/useMaterials.ts` (cached DB queries) and `src/hooks/useCalculation.ts` (POST /api/calculate mutation with debounce).

### Task 3: CalculationModeToggle component

Simple radio toggle for EC vs Quick mode.

### Task 4: SystemSection component

Sprungmaß input, field count stepper (1-5), cantilever checkboxes, dynamic span inputs.

### Task 5: LoadsSection + LoadRow components

Dynamic load table with add/remove, cascading lastfall→kategorie dropdowns, NKL selector, eigengewicht toggle.

### Task 6: CrossSectionSection component

3-variant material selection with cascading dropdowns (gruppe→typ→festigkeitsklasse), dimensions (b/h), variant radio selector.

### Task 7: DeflectionSection component

Situation preset selector (Allgemein / Überhöht / Eigene Werte), pre-camber input, limit display/inputs.

### Task 8: InputForm container + App integration

Wire all sections together, connect to store, trigger calculations on change, integrate into App.tsx layout.
