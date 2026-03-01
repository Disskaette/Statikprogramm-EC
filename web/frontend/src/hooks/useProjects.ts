/**
 * React Query hooks for the project and position API endpoints.
 *
 * staleTime is set to 30 seconds for project lists (user may create or modify
 * projects from another session), vs. Infinity for static material data.
 *
 * API routes (FastAPI, proxied via Vite in dev):
 *   GET /api/projects
 *   GET /api/projects/{uuid}/positions
 *   GET /api/projects/{uuid}/positions/{rel_path}
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Project, Position } from "@/types/project";

// ---------------------------------------------------------------------------
// All projects list
// ---------------------------------------------------------------------------

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/api/projects"),
    staleTime: 30_000,
  });
}

// ---------------------------------------------------------------------------
// Positions within a project
// ---------------------------------------------------------------------------

/**
 * API response shape for the positions endpoint (since Phase 6).
 * The endpoint now returns `{ positions: [...], folders: [...] }` instead of
 * a flat Position[].
 */
interface PositionsResponse {
  positions: Position[];
  folders: string[];
}

export function usePositions(projectId: string | null) {
  return useQuery({
    queryKey: ["positions", projectId],
    queryFn: async () => {
      const raw = await api.get<PositionsResponse | Position[]>(
        `/api/projects/${projectId}/positions`,
      );
      // Handle both old (plain array) and new (object) response formats
      if (Array.isArray(raw)) {
        return { positions: raw, folders: [] as string[] };
      }
      return raw;
    },
    enabled: !!projectId,
    staleTime: 30_000,
  });
}
