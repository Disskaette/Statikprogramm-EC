/**
 * useLocalProjectActions – load and save positions from/to local disk.
 *
 * Mirrors the API surface of useProjectActions but uses the File System
 * Access API instead of HTTP calls.
 *
 * Calculations always go to the server (POST /api/calculate) regardless
 * of whether the position is local or server-side.
 */

import { useCallback, useState } from "react";
import { useBeamStore } from "@/stores/useBeamStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useLocalProjectStore } from "@/stores/useLocalProjectStore";
import {
  readPositionFile,
  writePositionFile,
  deletePositionFile,
} from "@/fs/useLocalFileSystem";
import type { HandleKey } from "@/types/localProject";
import type { CalculationRequest } from "@/types/beam";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UseLocalProjectActionsResult {
  isLoading: boolean;
  error: string | null;
  loadLocalPosition: (key: HandleKey, relativePath: string) => Promise<void>;
  saveLocalPosition: () => Promise<void>;
  createLocalPosition: (
    key: HandleKey,
    options: {
      position_nummer: string;
      position_name: string;
      subfolder?: string;
    }
  ) => Promise<void>;
  deleteLocalPosition: (key: HandleKey, relativePath: string) => Promise<void>;
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useLocalProjectActions(): UseLocalProjectActionsResult {
  const loadFromRequest = useBeamStore((s) => s.loadFromRequest);
  const buildRequest = useBeamStore((s) => s.buildRequest);

  const setCurrentPosition = useProjectStore((s) => s.setCurrentPosition);
  const setDirty = useProjectStore((s) => s.setDirty);
  const setProjectMode = useProjectStore((s) => s.setProjectMode);
  const currentPositionPath = useProjectStore((s) => s.currentPositionPath);
  const currentLocalProjectKey = useProjectStore((s) => s.currentLocalProjectKey);

  const projects = useLocalProjectStore((s) => s.projects);
  const refreshProject = useLocalProjectStore((s) => s.refreshProject);

  const clearPosition = useProjectStore((s) => s.clearPosition);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // loadLocalPosition
  // -------------------------------------------------------------------------

  const loadLocalPosition = useCallback(
    async (key: HandleKey, relativePath: string) => {
      const project = projects.find((p) => p.key === key);
      if (!project) {
        setError(`Lokales Projekt nicht gefunden: ${key}`);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const position = await readPositionFile(project.handle, relativePath);

        const moduleData = position.modules[
          "durchlauftraeger"
        ] as CalculationRequest | undefined;

        if (moduleData) {
          loadFromRequest(moduleData);
        }

        const displayName = `${position.position_nummer} – ${position.position_name}`;
        setCurrentPosition(relativePath, displayName);
        setProjectMode("local", key);
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Fehler beim Laden der Position";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [projects, loadFromRequest, setCurrentPosition, setProjectMode]
  );

  // -------------------------------------------------------------------------
  // saveLocalPosition
  // -------------------------------------------------------------------------

  const saveLocalPosition = useCallback(async () => {
    if (!currentLocalProjectKey || !currentPositionPath) {
      setError("Keine lokale Position zum Speichern ausgewählt");
      return;
    }

    const project = projects.find((p) => p.key === currentLocalProjectKey);
    if (!project) {
      setError(`Lokales Projekt nicht gefunden: ${currentLocalProjectKey}`);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const request = buildRequest();

      // Read existing metadata to preserve position_nummer, position_name, etc.
      let existingMeta: Record<string, unknown> = {};
      try {
        const pos = await readPositionFile(project.handle, currentPositionPath);
        existingMeta = {
          position_nummer: pos.position_nummer,
          position_name: pos.position_name,
          created: pos.created,
          active_module: pos.active_module,
        };
      } catch {
        // File may not exist yet – ignore, write with defaults
      }

      await writePositionFile(project.handle, currentPositionPath, {
        ...existingMeta,
        active_module: "durchlauftraeger",
        modules: { durchlauftraeger: request },
      });

      setDirty(false);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Fehler beim Speichern der Position";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [
    currentLocalProjectKey,
    currentPositionPath,
    projects,
    buildRequest,
    setDirty,
  ]);

  // -------------------------------------------------------------------------
  // createLocalPosition
  // -------------------------------------------------------------------------

  const createLocalPosition = useCallback(
    async (
      key: HandleKey,
      options: {
        position_nummer: string;
        position_name: string;
        subfolder?: string;
      }
    ) => {
      const project = projects.find((p) => p.key === key);
      if (!project) {
        setError(`Lokales Projekt nicht gefunden: ${key}`);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        // Build a safe filename from nummer + name
        const safeName = `${options.position_nummer}_${options.position_name}`
          .replace(/[^a-zA-Z0-9.\-_ ]/g, "_")
          .replace(/ /g, "_");
        const fileName = `Position_${safeName}.json`;
        const relativePath = options.subfolder
          ? `${options.subfolder}/${fileName}`
          : fileName;

        const request = buildRequest();
        const now = new Date().toISOString();

        await writePositionFile(project.handle, relativePath, {
          position_nummer: options.position_nummer,
          position_name: options.position_name,
          created: now,
          active_module: "durchlauftraeger",
          modules: { durchlauftraeger: request },
        });

        const displayName = `${options.position_nummer} – ${options.position_name}`;
        setCurrentPosition(relativePath, displayName);
        setProjectMode("local", key);

        // Refresh the project's positions list in the store
        await refreshProject(key);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Fehler beim Erstellen der Position"
        );
      } finally {
        setIsLoading(false);
      }
    },
    [projects, buildRequest, setCurrentPosition, setProjectMode, refreshProject]
  );

  // -------------------------------------------------------------------------
  // deleteLocalPosition
  // -------------------------------------------------------------------------

  const deleteLocalPosition = useCallback(
    async (key: HandleKey, relativePath: string) => {
      const project = projects.find((p) => p.key === key);
      if (!project) {
        setError(`Lokales Projekt nicht gefunden: ${key}`);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        await deletePositionFile(project.handle, relativePath);

        // Clear form if the deleted position was active
        if (
          currentPositionPath === relativePath &&
          currentLocalProjectKey === key
        ) {
          clearPosition();
        }

        await refreshProject(key);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Fehler beim Löschen der Position"
        );
      } finally {
        setIsLoading(false);
      }
    },
    [
      projects,
      currentPositionPath,
      currentLocalProjectKey,
      clearPosition,
      refreshProject,
    ]
  );

  // -------------------------------------------------------------------------

  const clearError = useCallback(() => setError(null), []);

  return {
    isLoading,
    error,
    loadLocalPosition,
    saveLocalPosition,
    createLocalPosition,
    deleteLocalPosition,
    clearError,
  };
}
