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
import { useQueryClient } from "@tanstack/react-query";
import { useBeamStore } from "@/stores/useBeamStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useLocalProjectStore } from "@/stores/useLocalProjectStore";
import {
  pickDirectory,
  readPositionFile,
  writePositionFile,
  deletePositionFile,
} from "@/fs/useLocalFileSystem";
import type { Project } from "@/types/project";
import { api } from "@/lib/api";
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
  uploadToServer: (
    key: HandleKey,
    options: { projectName: string; visibility: "private" | "shared" }
  ) => Promise<void>;
  downloadToLocal: (projectId: string, projectName: string) => Promise<void>;
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useLocalProjectActions(): UseLocalProjectActionsResult {
  const queryClient = useQueryClient();

  const loadFromRequest = useBeamStore((s) => s.loadFromRequest);
  const buildRequest = useBeamStore((s) => s.buildRequest);

  const setCurrentPosition = useProjectStore((s) => s.setCurrentPosition);
  const setDirty = useProjectStore((s) => s.setDirty);
  const setProjectMode = useProjectStore((s) => s.setProjectMode);
  const currentPositionPath = useProjectStore((s) => s.currentPositionPath);
  const currentLocalProjectKey = useProjectStore((s) => s.currentLocalProjectKey);

  const projects = useLocalProjectStore((s) => s.projects);
  const refreshProject = useLocalProjectStore((s) => s.refreshProject);
  const addProject = useLocalProjectStore((s) => s.addProject);

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
  // uploadToServer
  // -------------------------------------------------------------------------

  const uploadToServer = useCallback(
    async (
      key: HandleKey,
      options: { projectName: string; visibility: "private" | "shared" }
    ) => {
      const project = projects.find((p) => p.key === key);
      if (!project) {
        setError(`Lokales Projekt nicht gefunden: ${key}`);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        // 1. Create project on server
        const newProject = await api.post<{ uuid: string; path: string }>(
          "/api/projects",
          {
            name: options.projectName,
            description: project.meta.description,
          }
        );

        // 2. Upload all positions
        for (const pos of project.positions) {
          // Read full position data (includes modules)
          const fullPos = await readPositionFile(project.handle, pos.relative_path);

          // Determine subfolder (everything before the last "/" segment)
          const parts = pos.relative_path.split("/");
          const subfolder = parts.length > 1 ? parts.slice(0, -1).join("/") : "";

          // Create position entry on server
          await api.post<{ relative_path: string }>(
            `/api/projects/${newProject.uuid}/positions`,
            {
              position_nummer: fullPos.position_nummer,
              position_name: fullPos.position_name,
              subfolder,
              active_module: fullPos.active_module ?? "durchlauftraeger",
            }
          );

          // Save full module data into the position
          await api.put(
            `/api/projects/${newProject.uuid}/positions/${pos.relative_path}`,
            {
              position_nummer: fullPos.position_nummer,
              position_name: fullPos.position_name,
              active_module: fullPos.active_module ?? "durchlauftraeger",
              modules: fullPos.modules,
            }
          );
        }

        // 3. Refresh server projects list
        await queryClient.invalidateQueries({ queryKey: ["projects"] });
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Fehler beim Hochladen auf den Server"
        );
      } finally {
        setIsLoading(false);
      }
    },
    [projects, queryClient]
  );

  // -------------------------------------------------------------------------
  // downloadToLocal
  // -------------------------------------------------------------------------

  const downloadToLocal = useCallback(
    async (projectId: string, projectName: string) => {
      setIsLoading(true);
      setError(null);
      try {
        // 1. Pick a target folder
        let targetHandle: FileSystemDirectoryHandle;
        try {
          targetHandle = await pickDirectory();
        } catch (err) {
          if (err instanceof Error && err.name === "AbortError") return; // user cancelled
          throw err;
        }

        // 2. Read all positions from server
        const positionsResponse = await api.get<{
          positions: { relative_path: string }[];
          folders: string[];
        }>(`/api/projects/${projectId}/positions`);

        // 3. Read project metadata from server projects list
        const serverProjects = await api.get<Project[]>("/api/projects");
        const project = serverProjects.find((p) => p.uuid === projectId);

        // 4. Write project.json to target folder
        await writePositionFile(targetHandle, "project.json", {
          uuid: projectId,
          name: project?.name ?? projectName,
          created: project?.created ?? new Date().toISOString(),
          last_modified: new Date().toISOString(),
          description: project?.description ?? "",
          visibility: project?.visibility ?? "private",
        });

        // 5. Download and write each position file
        for (const pos of positionsResponse.positions) {
          const fullPos = await api.get<{
            position_nummer: string;
            position_name: string;
            created: string;
            active_module: string;
            modules: Record<string, unknown>;
          }>(`/api/projects/${projectId}/positions/${pos.relative_path}`);

          await writePositionFile(targetHandle, pos.relative_path, {
            position_nummer: fullPos.position_nummer,
            position_name: fullPos.position_name,
            created: fullPos.created,
            active_module: fullPos.active_module,
            modules: fullPos.modules,
          });
        }

        // 6. Register the downloaded folder as a local project
        await addProject(targetHandle);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Fehler beim lokalen Speichern"
        );
      } finally {
        setIsLoading(false);
      }
    },
    [queryClient, addProject]
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
    uploadToServer,
    downloadToLocal,
    clearError,
  };
}
