/**
 * ProjectExplorer – sidebar component for project and position navigation.
 *
 * Structure:
 *  1. Project selector (dropdown + "new project" inline form)
 *  2. Position list grouped by subfolder, with load-on-click
 *  3. Bottom bar: current position name, save button, new-position button
 */

import { useState, type KeyboardEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useProjects, usePositions } from "@/hooks/useProjects";
import { useProjectActions } from "@/hooks/useProjectActions";
import { useProjectStore } from "@/stores/useProjectStore";
import { api } from "@/lib/api";
import type { Project, Position } from "@/types/project";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Extract the subfolder from a relative path.
 * "EG/Position_1_01.json"  → "EG"
 * "Position_1_01.json"     → "" (root level, no subfolder)
 */
function getSubfolder(relativePath: string): string {
  const parts = relativePath.split("/");
  return parts.length > 1 ? parts[0] : "";
}

/** Format an ISO timestamp as a short locale date string */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
    });
  } catch {
    return "";
  }
}

/** Build a display label from position fields */
function positionLabel(pos: Position): string {
  return `${pos.position_nummer} – ${pos.position_name}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface FolderGroupProps {
  folder: string;
  positions: Position[];
  activePositionPath: string | null;
  onLoad: (relativePath: string) => void;
}

function FolderGroup({
  folder,
  positions,
  activePositionPath,
  onLoad,
}: FolderGroupProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="mb-1">
      {/* Folder header – only shown when there is a named subfolder */}
      {folder && (
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="flex w-full items-center gap-1 px-2 py-1 text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wide hover:text-[var(--foreground)] transition-colors"
        >
          {/* Chevron indicator */}
          <span
            className="inline-block transition-transform"
            style={{ transform: collapsed ? "rotate(-90deg)" : "rotate(0deg)" }}
          >
            ▾
          </span>
          {folder}
        </button>
      )}

      {!collapsed &&
        positions.map((pos) => {
          const isActive = pos.relative_path === activePositionPath;
          return (
            <button
              key={pos.relative_path}
              type="button"
              onClick={() => onLoad(pos.relative_path)}
              className={[
                "flex w-full flex-col items-start gap-0.5 px-3 py-1.5 text-left",
                "transition-colors hover:bg-[var(--primary)]/10",
                isActive
                  ? "bg-[var(--primary)]/15 border-l-2 border-[var(--primary)]"
                  : "border-l-2 border-transparent",
              ].join(" ")}
            >
              <span
                className={`text-xs leading-tight ${isActive ? "font-semibold text-[var(--primary)]" : "text-[var(--foreground)]"}`}
              >
                {positionLabel(pos)}
              </span>
              <span className="text-[10px] text-[var(--muted-foreground)]">
                {formatDate(pos.last_modified)}
              </span>
            </button>
          );
        })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline input row (used for "new project" and "new position" forms)
// ---------------------------------------------------------------------------

interface InlineFormProps {
  placeholder: string;
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

function InlineInput({ placeholder, onConfirm, onCancel }: InlineFormProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (trimmed) onConfirm(trimmed);
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") submit();
    if (e.key === "Escape") onCancel();
  };

  return (
    <div className="flex gap-1 px-2 py-1">
      <input
        autoFocus
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKey}
        placeholder={placeholder}
        className={[
          "flex-1 min-w-0 rounded border border-[var(--border)] bg-[var(--background)]",
          "px-2 py-0.5 text-xs text-[var(--foreground)]",
          "focus:outline-none focus:ring-1 focus:ring-[var(--primary)]",
        ].join(" ")}
      />
      <button
        type="button"
        onClick={submit}
        className="rounded bg-[var(--primary)] px-1.5 py-0.5 text-xs text-white hover:opacity-90"
      >
        OK
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="rounded border border-[var(--border)] px-1.5 py-0.5 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
      >
        ✕
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// New-position dialog (inline, two fields)
// ---------------------------------------------------------------------------

interface NewPositionFormProps {
  onConfirm: (nummer: string, name: string, subfolder: string) => void;
  onCancel: () => void;
}

function NewPositionForm({ onConfirm, onCancel }: NewPositionFormProps) {
  const [nummer, setNummer] = useState("");
  const [name, setName] = useState("");
  const [subfolder, setSubfolder] = useState("");

  const submit = () => {
    const n = nummer.trim();
    const nm = name.trim();
    if (n && nm) onConfirm(n, nm, subfolder.trim());
  };

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") onCancel();
  };

  return (
    <div
      className="mx-2 my-1 rounded border border-[var(--border)] bg-[var(--background)] p-2 space-y-1.5"
      onKeyDown={handleKey}
    >
      <p className="text-[10px] font-semibold text-[var(--muted-foreground)] uppercase tracking-wide">
        Neue Position
      </p>

      <input
        autoFocus
        type="text"
        value={nummer}
        onChange={(e) => setNummer(e.target.value)}
        placeholder="Nr. (z.B. 1.01)"
        className="w-full rounded border border-[var(--border)] bg-[var(--background)] px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
      />
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Name (z.B. HT 1 – Wohnzimmer)"
        className="w-full rounded border border-[var(--border)] bg-[var(--background)] px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
      />
      <input
        type="text"
        value={subfolder}
        onChange={(e) => setSubfolder(e.target.value)}
        placeholder="Unterordner (optional, z.B. EG)"
        className="w-full rounded border border-[var(--border)] bg-[var(--background)] px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
      />

      <div className="flex gap-1 pt-0.5">
        <button
          type="button"
          onClick={submit}
          disabled={!nummer.trim() || !name.trim()}
          className="flex-1 rounded bg-[var(--primary)] px-2 py-1 text-xs text-white hover:opacity-90 disabled:opacity-40"
        >
          Erstellen
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded border border-[var(--border)] px-2 py-1 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        >
          Abbrechen
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ProjectExplorer() {
  const queryClient = useQueryClient();

  // Project / position state
  const { currentProjectId, currentPositionPath, currentPositionName, isDirty, setCurrentProject } =
    useProjectStore();

  const { data: projects, isLoading: loadingProjects } = useProjects();
  const { data: positions, isLoading: loadingPositions } = usePositions(currentProjectId);

  const { isLoading: actionLoading, error: actionError, loadPosition, savePosition, createPosition, clearError } =
    useProjectActions();

  // isDirty comes from useProjectStore – it is set by InputForm on every user edit
  // and cleared by savePosition() after a successful PUT.

  // UI state
  const [showNewProject, setShowNewProject] = useState(false);
  const [showNewPosition, setShowNewPosition] = useState(false);

  // ---- Project selection ----

  const handleProjectChange = (uuid: string) => {
    setCurrentProject(uuid || null);
  };

  const handleCreateProject = async (name: string) => {
    setShowNewProject(false);
    try {
      const project = await api.post<Project>("/api/projects", {
        name,
        description: "",
      });
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      setCurrentProject(project.uuid);
    } catch (err) {
      console.error("Projekt konnte nicht erstellt werden:", err);
    }
  };

  // ---- Position actions ----

  const handleLoadPosition = (relativePath: string) => {
    if (!currentProjectId) return;
    loadPosition(currentProjectId, relativePath);
  };

  const handleSave = () => {
    savePosition();
  };

  const handleCreatePosition = (
    nummer: string,
    name: string,
    subfolder: string
  ) => {
    setShowNewPosition(false);
    if (!currentProjectId) return;
    createPosition(currentProjectId, {
      position_nummer: nummer,
      position_name: name,
      subfolder: subfolder || undefined,
    });
  };

  // ---- Group positions by subfolder ----

  const groupedPositions: Map<string, Position[]> = new Map();
  if (positions) {
    for (const pos of positions) {
      const folder = getSubfolder(pos.relative_path);
      if (!groupedPositions.has(folder)) {
        groupedPositions.set(folder, []);
      }
      groupedPositions.get(folder)!.push(pos);
    }
  }

  // Sort: root level ("") first, then alphabetical by folder name
  const sortedFolders = Array.from(groupedPositions.keys()).sort((a, b) => {
    if (a === "") return -1;
    if (b === "") return 1;
    return a.localeCompare(b, "de");
  });

  // ---- Render ----

  return (
    <div className="flex h-full flex-col">
      {/* ------------------------------------------------------------------ */}
      {/* Top: Project selector                                               */}
      {/* ------------------------------------------------------------------ */}
      <div className="shrink-0 border-b border-[var(--border)] p-2">
        <p className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
          Projekt
        </p>

        {loadingProjects ? (
          <p className="px-1 text-xs text-[var(--muted-foreground)] italic">
            Lade Projekte…
          </p>
        ) : (
          <>
            <div className="flex gap-1">
              <select
                value={currentProjectId ?? ""}
                onChange={(e) => handleProjectChange(e.target.value)}
                className={[
                  "flex-1 min-w-0 rounded border border-[var(--border)]",
                  "bg-[var(--background)] px-2 py-1 text-xs text-[var(--foreground)]",
                  "focus:outline-none focus:ring-1 focus:ring-[var(--primary)]",
                ].join(" ")}
              >
                <option value="">– Projekt wählen –</option>
                {projects?.map((p) => (
                  <option key={p.uuid} value={p.uuid}>
                    {p.name}
                  </option>
                ))}
              </select>

              <button
                type="button"
                title="Neues Projekt"
                onClick={() => setShowNewProject((v) => !v)}
                className={[
                  "shrink-0 rounded border border-[var(--border)] px-2 py-1 text-xs",
                  "hover:bg-[var(--primary)]/10 transition-colors",
                  showNewProject ? "bg-[var(--primary)]/10" : "",
                ].join(" ")}
              >
                +
              </button>
            </div>

            {showNewProject && (
              <InlineInput
                placeholder="Projektname"
                onConfirm={handleCreateProject}
                onCancel={() => setShowNewProject(false)}
              />
            )}
          </>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Middle: Position list (scrollable)                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 overflow-y-auto py-1">
        {!currentProjectId ? (
          <p className="px-3 py-2 text-xs text-[var(--muted-foreground)] italic">
            Kein Projekt gewählt
          </p>
        ) : loadingPositions ? (
          <p className="px-3 py-2 text-xs text-[var(--muted-foreground)] italic">
            Lade Positionen…
          </p>
        ) : !positions || positions.length === 0 ? (
          <p className="px-3 py-2 text-xs text-[var(--muted-foreground)] italic">
            Keine Positionen vorhanden
          </p>
        ) : (
          sortedFolders.map((folder) => (
            <FolderGroup
              key={folder}
              folder={folder}
              positions={groupedPositions.get(folder)!}
              activePositionPath={currentPositionPath}
              onLoad={handleLoadPosition}
            />
          ))
        )}

        {/* Error banner */}
        {actionError && (
          <div className="mx-2 my-1 rounded bg-red-500/10 px-2 py-1.5 text-xs text-red-600 dark:text-red-400">
            <div className="flex items-start justify-between gap-1">
              <span>{actionError}</span>
              <button
                type="button"
                onClick={clearError}
                className="shrink-0 text-[10px] opacity-70 hover:opacity-100"
              >
                ✕
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Bottom: Save bar                                                    */}
      {/* ------------------------------------------------------------------ */}
      <div className="shrink-0 border-t border-[var(--border)] p-2 space-y-2">
        {/* Current position indicator */}
        <div className="px-1">
          {currentPositionName ? (
            <div className="flex items-center gap-1">
              <span
                className="truncate text-[10px] text-[var(--foreground)]"
                title={currentPositionName}
              >
                {currentPositionName}
              </span>
              {isDirty && (
                <span
                  className="shrink-0 text-[10px] text-amber-500"
                  title="Ungespeicherte Änderungen"
                >
                  ●
                </span>
              )}
            </div>
          ) : (
            <span className="text-[10px] text-[var(--muted-foreground)] italic">
              Keine Position geladen
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-1">
          {/* Save button – only visible when a position is loaded */}
          {currentPositionPath && (
            <button
              type="button"
              onClick={handleSave}
              disabled={actionLoading || !isDirty}
              className={[
                "flex-1 rounded px-2 py-1 text-xs transition-colors",
                isDirty
                  ? "bg-[var(--primary)] text-white hover:opacity-90"
                  : "border border-[var(--border)] text-[var(--muted-foreground)]",
                "disabled:opacity-50",
              ].join(" ")}
              title={isDirty ? "Änderungen speichern" : "Keine Änderungen"}
            >
              {actionLoading ? "…" : "Speichern"}
            </button>
          )}

          {/* New position button – only when a project is selected */}
          {currentProjectId && (
            <button
              type="button"
              onClick={() => setShowNewPosition((v) => !v)}
              disabled={actionLoading}
              className={[
                "rounded border border-[var(--border)] px-2 py-1 text-xs",
                "hover:bg-[var(--primary)]/10 transition-colors",
                showNewPosition ? "bg-[var(--primary)]/10" : "",
                currentPositionPath ? "" : "flex-1",
              ].join(" ")}
            >
              Neue Position
            </button>
          )}
        </div>

        {/* Inline new-position form */}
        {showNewPosition && currentProjectId && (
          <NewPositionForm
            onConfirm={handleCreatePosition}
            onCancel={() => setShowNewPosition(false)}
          />
        )}
      </div>
    </div>
  );
}
