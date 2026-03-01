/**
 * useProjectActions – load and save positions via the project API.
 *
 * Loading:
 *   Fetches a position by relative_path, extracts the "durchlauftraeger"
 *   module data (which is stored in CalculationRequest shape), and calls
 *   useBeamStore.loadFromRequest() to bulk-populate the form.
 *
 * Saving:
 *   Reads the current form state via useBeamStore.buildRequest(), wraps it
 *   in the expected position payload, and PUTs it to the API.
 *   On success, marks the position as clean (isDirty = false) and
 *   invalidates the positions query cache.
 *
 * Creating a new position:
 *   POSTs to /api/projects/{uuid}/positions with the new position metadata.
 *   Then immediately saves the current form state into it.
 */

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import type { CalculationRequest } from "@/types/beam";
import type { Position } from "@/types/project";
import { useBeamStore } from "@/stores/useBeamStore";
import { useProjectStore } from "@/stores/useProjectStore";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CreatePositionOptions {
  position_nummer: string;
  position_name: string;
  subfolder?: string;
}

interface UseProjectActionsResult {
  /** True while any async action is in flight */
  isLoading: boolean;
  /** Last error message, or null */
  error: string | null;
  /** Load a position into the form */
  loadPosition: (projectId: string, relativePath: string) => Promise<void>;
  /** Save the current form state to the active position */
  savePosition: () => Promise<void>;
  /** Create a new position in the given project and immediately save form state into it */
  createPosition: (
    projectId: string,
    options: CreatePositionOptions
  ) => Promise<void>;
  /** Delete a single position */
  deletePosition: (projectId: string, relativePath: string) => Promise<void>;
  /** Delete multiple positions in sequence */
  deletePositions: (projectId: string, relativePaths: string[]) => Promise<void>;
  /** Rename a position (changes filename, position_nummer, position_name) */
  renamePosition: (
    projectId: string,
    relativePath: string,
    newNummer: string,
    newName: string,
  ) => Promise<void>;
  /** Duplicate a position (creates a copy with "(Kopie)" suffix) */
  duplicatePosition: (projectId: string, relativePath: string) => Promise<void>;
  /** Move a position to a different subfolder (empty string = project root) */
  movePosition: (
    projectId: string,
    relativePath: string,
    targetFolder: string,
  ) => Promise<void>;
  /** Create a new subfolder in the project */
  createFolder: (
    projectId: string,
    folderName: string,
    parentFolder?: string,
  ) => Promise<void>;
  /** Delete a subfolder and all positions inside it */
  deleteFolder: (projectId: string, folderPath: string) => Promise<void>;
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useProjectActions(): UseProjectActionsResult {
  const queryClient = useQueryClient();

  const loadFromRequest = useBeamStore((s) => s.loadFromRequest);
  const buildRequest = useBeamStore((s) => s.buildRequest);

  const {
    currentProjectId,
    currentPositionPath,
    setCurrentPosition,
    setDirty,
    clearPosition,
  } = useProjectStore();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // loadPosition
  // -------------------------------------------------------------------------

  const loadPosition = useCallback(
    async (projectId: string, relativePath: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const position = await api.get<Position>(
          `/api/projects/${projectId}/positions/${relativePath}`
        );

        // The durchlauftraeger module stores data in CalculationRequest shape.
        // Cast via unknown because modules is Record<string, unknown>.
        const moduleData = position.modules[
          "durchlauftraeger"
        ] as CalculationRequest | undefined;

        if (moduleData) {
          loadFromRequest(moduleData);
        }

        // Update project store: mark position as active and clean
        const displayName = `${position.position_nummer} – ${position.position_name}`;
        setCurrentPosition(position.relative_path, displayName);
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Fehler beim Laden der Position";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [loadFromRequest, setCurrentPosition]
  );

  // -------------------------------------------------------------------------
  // savePosition
  // -------------------------------------------------------------------------

  const savePosition = useCallback(async () => {
    if (!currentProjectId || !currentPositionPath) {
      setError("Keine Position zum Speichern ausgewählt");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const request = buildRequest();

      // The PUT payload mirrors the position JSON structure.
      // We preserve position_nummer and position_name by re-reading from the
      // current position name string stored in the project store.
      await api.put<Position>(
        `/api/projects/${currentProjectId}/positions/${currentPositionPath}`,
        {
          // Wrap calculation data inside the modules dict under the module key
          modules: {
            durchlauftraeger: request,
          },
          active_module: "durchlauftraeger",
        }
      );

      // Clear dirty flag and refresh the positions list
      setDirty(false);
      await queryClient.invalidateQueries({
        queryKey: ["positions", currentProjectId],
      });
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Fehler beim Speichern der Position";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [currentProjectId, currentPositionPath, buildRequest, setDirty, queryClient]);

  // -------------------------------------------------------------------------
  // createPosition
  // -------------------------------------------------------------------------

  const createPosition = useCallback(
    async (projectId: string, options: CreatePositionOptions) => {
      setIsLoading(true);
      setError(null);
      try {
        const newPosition = await api.post<Position>(
          `/api/projects/${projectId}/positions`,
          {
            position_nummer: options.position_nummer,
            position_name: options.position_name,
            subfolder: options.subfolder,
            active_module: "durchlauftraeger",
          }
        );

        // Immediately save current form state into the new position
        const request = buildRequest();
        await api.put<Position>(
          `/api/projects/${projectId}/positions/${newPosition.relative_path}`,
          {
            modules: { durchlauftraeger: request },
            active_module: "durchlauftraeger",
          }
        );

        // Update project store
        const displayName = `${newPosition.position_nummer} – ${newPosition.position_name}`;
        setCurrentPosition(newPosition.relative_path, displayName);

        // Refresh positions list
        await queryClient.invalidateQueries({
          queryKey: ["positions", projectId],
        });
        // Also refresh projects list in case the position count changed
        await queryClient.invalidateQueries({ queryKey: ["projects"] });
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Fehler beim Erstellen der Position";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [buildRequest, setCurrentPosition, queryClient]
  );

  // -------------------------------------------------------------------------
  // deletePosition
  // -------------------------------------------------------------------------

  const deletePosition = useCallback(
    async (projectId: string, relativePath: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await api.del(`/api/projects/${projectId}/positions/${relativePath}`);

        // If the deleted position was the active one, clear the form
        if (currentPositionPath === relativePath) {
          clearPosition();
        }

        await queryClient.invalidateQueries({
          queryKey: ["positions", projectId],
        });
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Fehler beim Löschen der Position";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [currentPositionPath, clearPosition, queryClient],
  );

  // -------------------------------------------------------------------------
  // deletePositions (bulk)
  // -------------------------------------------------------------------------

  const deletePositions = useCallback(
    async (projectId: string, relativePaths: string[]) => {
      setIsLoading(true);
      setError(null);
      try {
        for (const rp of relativePaths) {
          await api.del(`/api/projects/${projectId}/positions/${rp}`);
        }

        // If the active position was among the deleted ones, clear the form
        if (currentPositionPath && relativePaths.includes(currentPositionPath)) {
          clearPosition();
        }

        await queryClient.invalidateQueries({
          queryKey: ["positions", projectId],
        });
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Fehler beim Löschen der Positionen";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [currentPositionPath, clearPosition, queryClient],
  );

  // -------------------------------------------------------------------------
  // renamePosition
  // -------------------------------------------------------------------------

  const renamePosition = useCallback(
    async (
      projectId: string,
      relativePath: string,
      newNummer: string,
      newName: string,
    ) => {
      setIsLoading(true);
      setError(null);
      try {
        const updated = await api.patch<Position>(
          `/api/projects/${projectId}/positions/${relativePath}/rename`,
          { new_nummer: newNummer, new_name: newName },
        );

        // If the renamed position was the active one, update the store
        if (currentPositionPath === relativePath) {
          const displayName = `${updated.position_nummer} – ${updated.position_name}`;
          setCurrentPosition(updated.relative_path, displayName);
        }

        await queryClient.invalidateQueries({
          queryKey: ["positions", projectId],
        });
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Fehler beim Umbenennen der Position";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [currentPositionPath, setCurrentPosition, queryClient],
  );

  // -------------------------------------------------------------------------
  // duplicatePosition
  // -------------------------------------------------------------------------

  const duplicatePosition = useCallback(
    async (projectId: string, relativePath: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await api.post<Position>(
          `/api/projects/${projectId}/positions/${relativePath}/duplicate`,
          {},
        );

        await queryClient.invalidateQueries({
          queryKey: ["positions", projectId],
        });
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Fehler beim Duplizieren der Position";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [queryClient],
  );

  // -------------------------------------------------------------------------
  // movePosition
  // -------------------------------------------------------------------------

  const movePosition = useCallback(
    async (
      projectId: string,
      relativePath: string,
      targetFolder: string,
    ) => {
      setIsLoading(true);
      setError(null);
      try {
        const updated = await api.patch<Position>(
          `/api/projects/${projectId}/positions/${relativePath}/move`,
          { target_folder: targetFolder },
        );

        // If the moved position was the active one, update path in store
        if (currentPositionPath === relativePath) {
          const displayName = `${updated.position_nummer} – ${updated.position_name}`;
          setCurrentPosition(updated.relative_path, displayName);
        }

        await queryClient.invalidateQueries({
          queryKey: ["positions", projectId],
        });
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Fehler beim Verschieben der Position";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [currentPositionPath, setCurrentPosition, queryClient],
  );

  // -------------------------------------------------------------------------
  // createFolder
  // -------------------------------------------------------------------------

  const createFolder = useCallback(
    async (projectId: string, folderName: string, parentFolder?: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await api.post(`/api/projects/${projectId}/folders`, {
          folder_name: folderName,
          parent_folder: parentFolder ?? "",
        });

        await queryClient.invalidateQueries({
          queryKey: ["positions", projectId],
        });
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Fehler beim Erstellen des Ordners";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [queryClient],
  );

  // -------------------------------------------------------------------------
  // deleteFolder
  // -------------------------------------------------------------------------

  const deleteFolder = useCallback(
    async (projectId: string, folderPath: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await api.del(
          `/api/projects/${projectId}/folders/${folderPath}`,
        );

        // If the active position was inside the deleted folder, clear form
        if (
          currentPositionPath &&
          currentPositionPath.startsWith(folderPath + "/")
        ) {
          clearPosition();
        }

        await queryClient.invalidateQueries({
          queryKey: ["positions", projectId],
        });
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Fehler beim Löschen des Ordners";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [currentPositionPath, clearPosition, queryClient],
  );

  // -------------------------------------------------------------------------

  const clearError = useCallback(() => setError(null), []);

  return {
    isLoading,
    error,
    loadPosition,
    savePosition,
    createPosition,
    deletePosition,
    deletePositions,
    renamePosition,
    duplicatePosition,
    movePosition,
    createFolder,
    deleteFolder,
    clearError,
  };
}
