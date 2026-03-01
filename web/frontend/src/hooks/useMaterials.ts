/**
 * React Query hooks for caching material database lookups.
 *
 * All queries use staleTime: Infinity because material data (timber groups,
 * types, strength classes, load categories) is static at runtime – it only
 * changes when the backend database is updated and the server restarts.
 *
 * API routes (served by FastAPI via Vite proxy in dev):
 *   GET /api/materials/groups
 *   GET /api/materials/types?gruppe=<gruppe>
 *   GET /api/materials/strength-classes?gruppe=<gruppe>&typ=<typ>
 *   GET /api/materials/load-types
 *   GET /api/materials/load-categories?lastfall=<lastfall>
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Material groups (e.g. "Balken", "Brett", ...)
// ---------------------------------------------------------------------------

export function useMaterialGroups() {
  return useQuery({
    queryKey: ["materials", "groups"],
    queryFn: () => api.get<string[]>("/api/materials/groups"),
    staleTime: Infinity, // material data never changes at runtime
  });
}

// ---------------------------------------------------------------------------
// Material types within a group (e.g. "Nadelholz", "Laubholz")
// ---------------------------------------------------------------------------

export function useMaterialTypes(gruppe: string) {
  return useQuery({
    queryKey: ["materials", "types", gruppe],
    queryFn: () =>
      api.get<string[]>(
        `/api/materials/types?gruppe=${encodeURIComponent(gruppe)}`
      ),
    staleTime: Infinity,
    enabled: !!gruppe,
  });
}

// ---------------------------------------------------------------------------
// Strength classes for a given group + type (e.g. "C24", "GL28h")
// ---------------------------------------------------------------------------

export function useStrengthClasses(gruppe: string, typ: string) {
  return useQuery({
    queryKey: ["materials", "strength-classes", gruppe, typ],
    queryFn: () =>
      api.get<string[]>(
        `/api/materials/strength-classes?gruppe=${encodeURIComponent(gruppe)}&typ=${encodeURIComponent(typ)}`
      ),
    staleTime: Infinity,
    enabled: !!gruppe && !!typ,
  });
}

// ---------------------------------------------------------------------------
// Available load type identifiers (e.g. ["g", "p", "s", "w"])
// ---------------------------------------------------------------------------

export function useLoadTypes() {
  return useQuery({
    queryKey: ["materials", "load-types"],
    queryFn: () => api.get<string[]>("/api/materials/load-types"),
    staleTime: Infinity,
  });
}

// ---------------------------------------------------------------------------
// Load categories for a given lastfall identifier
//
// IMPORTANT: Category strings must match the DB values exactly when sent back
// to the API (e.g. "Nutzlast Kat. A: Wohnraum", NOT "Wohn- und Aufenthaltsräume").
// ---------------------------------------------------------------------------

export function useLoadCategories(lastfall: string) {
  return useQuery({
    queryKey: ["materials", "load-categories", lastfall],
    queryFn: () =>
      api.get<string[]>(
        `/api/materials/load-categories?lastfall=${encodeURIComponent(lastfall)}`
      ),
    staleTime: Infinity,
    enabled: !!lastfall,
  });
}
