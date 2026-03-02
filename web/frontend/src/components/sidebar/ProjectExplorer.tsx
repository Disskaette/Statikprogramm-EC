/**
 * ProjectExplorer – sidebar component for project and position navigation.
 *
 * Features:
 *  A. Tree View  – recursive FolderNode tree built from flat positions + folders arrays
 *  B. Context Menu – right-click menus for positions, folders, and multi-selection
 *  C. Multi-Select – Click / Ctrl+Click / Shift+Click with range support
 *  D. Drag & Drop  – manual mouse-event drag (no HTML5 DnD, no library)
 *  E. Project management – dropdown selector, new project inline form, bottom save bar
 */

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  type KeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useProjects, usePositions } from "@/hooks/useProjects";
import { useProjectActions } from "@/hooks/useProjectActions";
import { useProjectStore } from "@/stores/useProjectStore";
import { api } from "@/lib/api";
import type { Project, Position, FolderNode } from "@/types/project";
import { ContextMenu, type ContextMenuEntry } from "@/components/ui/ContextMenu";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { InputDialog } from "@/components/ui/InputDialog";

// =============================================================================
// A. Tree helpers
// =============================================================================

/** Extract the direct parent folder from a relative path (one level only). */
function getDirectFolder(relativePath: string): string {
  const parts = relativePath.split("/");
  return parts.length > 1 ? parts.slice(0, -1).join("/") : "";
}

/** Format an ISO timestamp as a short German locale date string. */
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

/** Build a display label from position fields. */
function positionLabel(pos: Position): string {
  return `${pos.position_nummer} – ${pos.position_name}`;
}

/**
 * Build a recursive FolderNode tree from a flat positions list + a list of
 * explicit folder paths (which may be empty).
 *
 * Sorting rule: sub-folders first (alphabetical), then positions by
 * position_nummer (lexicographic).
 */
function buildFolderTree(
  positions: Position[],
  folders: string[],
): FolderNode {
  // Map of folderPath -> FolderNode for quick lookup
  const nodeMap = new Map<string, FolderNode>();

  const root: FolderNode = {
    name: "",
    relativePath: "",
    positions: [],
    subfolders: [],
  };
  nodeMap.set("", root);

  // Helper: ensure a folder node exists (creates parents recursively)
  function ensureFolder(folderPath: string): FolderNode {
    if (nodeMap.has(folderPath)) return nodeMap.get(folderPath)!;

    const parts = folderPath.split("/");
    const name = parts[parts.length - 1];
    const parentPath = parts.slice(0, -1).join("/");

    const parentNode = ensureFolder(parentPath);

    const node: FolderNode = {
      name,
      relativePath: folderPath,
      positions: [],
      subfolders: [],
    };
    nodeMap.set(folderPath, node);
    parentNode.subfolders.push(node);
    return node;
  }

  // Create nodes for all explicit folders (even if empty)
  for (const f of folders) {
    if (f) ensureFolder(f);
  }

  // Place each position in its direct parent folder
  for (const pos of positions) {
    const folderPath = getDirectFolder(pos.relative_path);
    const folderNode = ensureFolder(folderPath);
    folderNode.positions.push(pos);
  }

  // Sort each node's children: sub-folders alphabetically, positions by nummer
  function sortNode(node: FolderNode) {
    node.subfolders.sort((a, b) => a.name.localeCompare(b.name, "de"));
    node.positions.sort((a, b) =>
      a.position_nummer.localeCompare(b.position_nummer, "de", {
        numeric: true,
      })
    );
    node.subfolders.forEach(sortNode);
  }
  sortNode(root);

  return root;
}

/**
 * Collect all visible position paths in tree order (depth-first pre-order),
 * respecting collapsed folders. Used for shift-range selection.
 */
function collectVisiblePaths(
  node: FolderNode,
  collapsedFolders: Set<string>,
  result: string[] = [],
): string[] {
  // Positions at this level first
  for (const pos of node.positions) {
    result.push(pos.relative_path);
  }
  // Then sub-folders (unless root – root never has its own collapse state)
  for (const sub of node.subfolders) {
    if (!collapsedFolders.has(sub.relativePath)) {
      collectVisiblePaths(sub, collapsedFolders, result);
    }
  }
  return result;
}

// =============================================================================
// B/C/D. State types
// =============================================================================

interface ContextMenuState {
  x: number;
  y: number;
  targetPath: string;
  targetType: "position" | "folder";
}

// Dialog union types
type DialogState =
  | { kind: "none" }
  | { kind: "confirmDeletePosition"; path: string }
  | { kind: "confirmDeletePositions"; paths: string[] }
  | { kind: "confirmDeleteFolder"; folderPath: string }
  | { kind: "renamePosition"; path: string; currentLabel: string }
  | { kind: "newFolder"; parentFolder: string };

// =============================================================================
// Sub-component: InlineInput (used for "new project" inline form)
// =============================================================================

interface InlineInputProps {
  placeholder: string;
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

function InlineInput({ placeholder, onConfirm, onCancel }: InlineInputProps) {
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
        &#x2715;
      </button>
    </div>
  );
}

// =============================================================================
// Sub-component: NewPositionForm
// =============================================================================

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

// =============================================================================
// Sub-component: PositionItem
// =============================================================================

interface PositionItemProps {
  pos: Position;
  isActive: boolean;
  isSelected: boolean;
  isDragTarget: boolean;
  onLoad: (path: string) => void;
  onMouseDown: (e: ReactMouseEvent<HTMLButtonElement>, path: string) => void;
  onContextMenu: (
    e: ReactMouseEvent<HTMLButtonElement>,
    path: string,
    type: "position"
  ) => void;
  onClick: (e: ReactMouseEvent<HTMLButtonElement>, path: string) => void;
}

function PositionItem({
  pos,
  isActive,
  isSelected,
  isDragTarget,
  onMouseDown,
  onContextMenu,
  onClick,
}: PositionItemProps) {
  const baseClasses = [
    "flex w-full flex-col items-start gap-0.5 px-3 py-1.5 text-left select-none",
    "transition-colors",
  ];

  let stateClasses: string;
  if (isDragTarget) {
    stateClasses =
      "bg-green-500/20 border-l-2 border-green-500";
  } else if (isActive) {
    stateClasses =
      "border-l-2 border-[var(--primary)] bg-[var(--primary)]/5";
  } else if (isSelected) {
    stateClasses =
      "border-l-2 border-[var(--primary)]/50 bg-[var(--primary)]/10";
  } else {
    stateClasses =
      "border-l-2 border-transparent hover:bg-[var(--primary)]/10";
  }

  return (
    <button
      type="button"
      data-position-path={pos.relative_path}
      onClick={(e) => onClick(e, pos.relative_path)}
      onMouseDown={(e) => onMouseDown(e, pos.relative_path)}
      onContextMenu={(e) => onContextMenu(e, pos.relative_path, "position")}
      className={[...baseClasses, stateClasses].join(" ")}
    >
      <span
        className={`text-xs leading-tight ${
          isActive
            ? "font-semibold text-[var(--primary)]"
            : "text-[var(--foreground)]"
        }`}
      >
        &#x1F4C4; {positionLabel(pos)}
      </span>
      <span className="text-[10px] text-[var(--muted-foreground)]">
        {formatDate(pos.last_modified)}
      </span>
    </button>
  );
}

// =============================================================================
// Sub-component: FolderGroup (recursive)
// =============================================================================

interface FolderGroupProps {
  node: FolderNode;
  depth: number;
  collapsedFolders: Set<string>;
  onToggleCollapse: (folderPath: string) => void;
  // Selection / active
  activePositionPath: string | null;
  selectedPaths: string[];
  // Drag state
  dragOverFolder: string | null;
  // Handlers passed from parent
  onPositionLoad: (path: string) => void;
  onPositionMouseDown: (
    e: ReactMouseEvent<HTMLButtonElement>,
    path: string
  ) => void;
  onPositionClick: (
    e: ReactMouseEvent<HTMLButtonElement>,
    path: string
  ) => void;
  onPositionContextMenu: (
    e: ReactMouseEvent<HTMLButtonElement>,
    path: string,
    type: "position"
  ) => void;
  onFolderContextMenu: (
    e: ReactMouseEvent<HTMLButtonElement>,
    folderPath: string,
    type: "folder"
  ) => void;
}

function FolderGroup({
  node,
  depth,
  collapsedFolders,
  onToggleCollapse,
  activePositionPath,
  selectedPaths,
  dragOverFolder,
  onPositionLoad,
  onPositionMouseDown,
  onPositionClick,
  onPositionContextMenu,
  onFolderContextMenu,
}: FolderGroupProps) {
  const isCollapsed = collapsedFolders.has(node.relativePath);
  const isFolderDragOver = dragOverFolder === node.relativePath;

  const indentClass = depth > 0 ? `pl-${Math.min(depth * 3, 12)}` : "";

  return (
    <div className="mb-0.5">
      {/* Folder header – only for named (non-root) folders */}
      {node.name && (
        <button
          type="button"
          data-folder-path={node.relativePath}
          onClick={() => onToggleCollapse(node.relativePath)}
          onContextMenu={(e) =>
            onFolderContextMenu(e, node.relativePath, "folder")
          }
          className={[
            "flex w-full items-center gap-1 px-2 py-1 text-left",
            "text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wide",
            "transition-colors",
            indentClass,
            isFolderDragOver
              ? "bg-green-500/20 border border-green-500 rounded"
              : "hover:text-[var(--foreground)] hover:bg-[var(--muted)]/40 rounded",
          ].join(" ")}
        >
          {/* Chevron */}
          <span
            className="inline-block transition-transform shrink-0 text-[10px]"
            style={{ transform: isCollapsed ? "rotate(-90deg)" : "rotate(0deg)" }}
          >
            &#x25BE;
          </span>
          <span>&#x1F4C1;</span>
          <span className="truncate">{node.name}</span>
        </button>
      )}

      {/* Children (positions + sub-folders), hidden when collapsed */}
      {!isCollapsed && (
        <div className={node.name ? `pl-3` : ""}>
          {/* Positions directly in this folder */}
          {node.positions.map((pos) => (
            <PositionItem
              key={pos.relative_path}
              pos={pos}
              isActive={pos.relative_path === activePositionPath}
              isSelected={selectedPaths.includes(pos.relative_path)}
              isDragTarget={false}
              onLoad={onPositionLoad}
              onMouseDown={onPositionMouseDown}
              onClick={onPositionClick}
              onContextMenu={onPositionContextMenu}
            />
          ))}

          {/* Recursive sub-folders */}
          {node.subfolders.map((sub) => (
            <FolderGroup
              key={sub.relativePath}
              node={sub}
              depth={depth + 1}
              collapsedFolders={collapsedFolders}
              onToggleCollapse={onToggleCollapse}
              activePositionPath={activePositionPath}
              selectedPaths={selectedPaths}
              dragOverFolder={dragOverFolder}
              onPositionLoad={onPositionLoad}
              onPositionMouseDown={onPositionMouseDown}
              onPositionClick={onPositionClick}
              onPositionContextMenu={onPositionContextMenu}
              onFolderContextMenu={onFolderContextMenu}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main component: ProjectExplorer
// =============================================================================

export function ProjectExplorer() {
  const queryClient = useQueryClient();

  // ---- Store ----------------------------------------------------------------
  const {
    currentProjectId,
    currentPositionPath,
    currentPositionName,
    isDirty,
    selectedPaths,
    isDragging,
    setCurrentProject,
    toggleSelection,
    clearSelection,
    setDragging,
  } = useProjectStore();

  // ---- Data fetching --------------------------------------------------------
  const { data: projects, isLoading: loadingProjects } = useProjects();
  const { data: positionsData, isLoading: loadingPositions } =
    usePositions(currentProjectId);

  const positions = positionsData?.positions ?? [];
  const folders = positionsData?.folders ?? [];

  // ---- Actions hook ---------------------------------------------------------
  const {
    isLoading: actionLoading,
    error: actionError,
    loadPosition,
    // savePosition removed – saving is now handled by useAutoSave in InputForm
    createPosition,
    deletePosition,
    deletePositions,
    renamePosition,
    duplicatePosition,
    movePosition,
    createFolder,
    deleteFolder,
    clearError,
  } = useProjectActions();

  // ---- UI state -------------------------------------------------------------
  const [showNewProject, setShowNewProject] = useState(false);
  const [showNewPosition, setShowNewPosition] = useState(false);

  // Context menu
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);

  // Modal dialogs
  const [dialog, setDialog] = useState<DialogState>({ kind: "none" });

  // Tree collapse state – Set of folder paths that are currently collapsed
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(
    new Set()
  );

  // Drag & drop
  const dragStartRef = useRef<{ x: number; y: number; path: string } | null>(
    null
  );
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null);

  // Anchor for shift-range selection (last non-shift clicked path)
  const selectionAnchorRef = useRef<string | null>(null);

  // ---- Build tree -----------------------------------------------------------
  const tree = buildFolderTree(positions, folders);

  // Flat ordered list of all visible paths (for shift-range selection)
  const visiblePaths = collectVisiblePaths(tree, collapsedFolders);

  // ==========================================================================
  // Project actions
  // ==========================================================================

  const handleProjectChange = (uuid: string) => {
    setCurrentProject(uuid || null);
    clearSelection();
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

  // ==========================================================================
  // Position actions
  // ==========================================================================

  const handleLoadPosition = useCallback(
    (relativePath: string) => {
      if (!currentProjectId) return;
      loadPosition(currentProjectId, relativePath);
    },
    [currentProjectId, loadPosition]
  );

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

  // ==========================================================================
  // C. Multi-select click handling
  // ==========================================================================

  const handlePositionClick = useCallback(
    (e: ReactMouseEvent<HTMLButtonElement>, path: string) => {
      const isMulti = e.ctrlKey || e.metaKey;
      const isShift = e.shiftKey;

      if (isShift && selectionAnchorRef.current) {
        // Shift+Click: range selection – select all visible positions between
        // the anchor and the clicked item (inclusive), without loading.
        const anchorIdx = visiblePaths.indexOf(selectionAnchorRef.current);
        const clickedIdx = visiblePaths.indexOf(path);
        if (anchorIdx !== -1 && clickedIdx !== -1) {
          const from = Math.min(anchorIdx, clickedIdx);
          const to = Math.max(anchorIdx, clickedIdx);
          const rangePaths = visiblePaths.slice(from, to + 1);
          // Replace selection with the range
          clearSelection();
          for (const rp of rangePaths) {
            toggleSelection(rp, true);
          }
        }
        return;
      }

      if (isMulti) {
        // Ctrl/Cmd+Click: toggle in selection, do NOT load
        toggleSelection(path, true);
        selectionAnchorRef.current = path;
        return;
      }

      // Plain click: clear selection, set single, load
      clearSelection();
      toggleSelection(path, false);
      selectionAnchorRef.current = path;
      handleLoadPosition(path);
    },
    [
      visiblePaths,
      clearSelection,
      toggleSelection,
      handleLoadPosition,
    ]
  );

  // ==========================================================================
  // B. Context menu handling
  // ==========================================================================

  const handlePositionContextMenu = useCallback(
    (
      e: ReactMouseEvent<HTMLButtonElement>,
      path: string,
      _type: "position"
    ) => {
      e.preventDefault();
      e.stopPropagation();

      // If right-clicked item is NOT in current selection, replace selection
      if (!selectedPaths.includes(path)) {
        clearSelection();
        toggleSelection(path, false);
        selectionAnchorRef.current = path;
      }

      setContextMenu({ x: e.clientX, y: e.clientY, targetPath: path, targetType: "position" });
    },
    [selectedPaths, clearSelection, toggleSelection]
  );

  const handleFolderContextMenu = useCallback(
    (
      e: ReactMouseEvent<HTMLButtonElement>,
      folderPath: string,
      _type: "folder"
    ) => {
      e.preventDefault();
      e.stopPropagation();
      setContextMenu({
        x: e.clientX,
        y: e.clientY,
        targetPath: folderPath,
        targetType: "folder",
      });
    },
    []
  );

  const closeContextMenu = useCallback(() => setContextMenu(null), []);

  // Build the context menu item list based on current state
  const contextMenuItems: ContextMenuEntry[] = (() => {
    if (!contextMenu || !currentProjectId) return [];

    const projectId = currentProjectId;

    // Multi-select: more than 1 item selected
    if (selectedPaths.length > 1 && contextMenu.targetType === "position") {
      return [
        {
          label: `Löschen (${selectedPaths.length} Elemente)`,
          danger: true,
          onClick: () => {
            setDialog({ kind: "confirmDeletePositions", paths: [...selectedPaths] });
          },
        },
      ];
    }

    if (contextMenu.targetType === "folder") {
      const folderPath = contextMenu.targetPath;
      return [
        {
          label: "Neuer Ordner…",
          onClick: () =>
            setDialog({ kind: "newFolder", parentFolder: folderPath }),
        },
        { separator: true as const },
        {
          label: "Löschen",
          danger: true,
          onClick: () =>
            setDialog({ kind: "confirmDeleteFolder", folderPath }),
        },
      ];
    }

    // Single position context menu
    const path = contextMenu.targetPath;
    const pos = positions.find((p) => p.relative_path === path);
    const parentFolder = path ? getDirectFolder(path) : "";

    return [
      {
        label: "Öffnen",
        onClick: () => handleLoadPosition(path),
      },
      { separator: true as const },
      {
        label: "Neuer Ordner…",
        onClick: () =>
          setDialog({ kind: "newFolder", parentFolder }),
      },
      { separator: true as const },
      {
        label: "Umbenennen",
        onClick: () => {
          if (pos) {
            setDialog({
              kind: "renamePosition",
              path,
              currentLabel: positionLabel(pos),
            });
          }
        },
      },
      {
        label: "Duplizieren",
        onClick: () => duplicatePosition(projectId, path),
      },
      { separator: true as const },
      {
        label: "Löschen",
        danger: true,
        onClick: () => setDialog({ kind: "confirmDeletePosition", path }),
      },
    ];
  })();

  // ==========================================================================
  // Dialog confirm handlers
  // ==========================================================================

  const handleDialogConfirm = useCallback(
    async (inputValue?: string) => {
      if (!currentProjectId) return;
      const projectId = currentProjectId;

      switch (dialog.kind) {
        case "confirmDeletePosition":
          await deletePosition(projectId, dialog.path);
          clearSelection();
          break;

        case "confirmDeletePositions":
          await deletePositions(projectId, dialog.paths);
          clearSelection();
          break;

        case "confirmDeleteFolder":
          await deleteFolder(projectId, dialog.folderPath);
          clearSelection();
          break;

        case "renamePosition": {
          // The InputDialog provides a combined "Nummer – Name" string.
          // We split on first " – " to separate nummer and name.
          const raw = inputValue ?? "";
          const sepIdx = raw.indexOf(" – ");
          let newNummer: string;
          let newName: string;
          if (sepIdx !== -1) {
            newNummer = raw.slice(0, sepIdx).trim();
            newName = raw.slice(sepIdx + 3).trim();
          } else {
            // Fallback: treat the whole input as the name, keep old nummer
            const pos = positions.find((p) => p.relative_path === dialog.path);
            newNummer = pos?.position_nummer ?? "";
            newName = raw.trim();
          }
          if (newNummer && newName) {
            await renamePosition(projectId, dialog.path, newNummer, newName);
          }
          break;
        }

        case "newFolder": {
          const folderName = inputValue?.trim() ?? "";
          if (folderName) {
            await createFolder(
              projectId,
              folderName,
              dialog.parentFolder || undefined
            );
          }
          break;
        }

        default:
          break;
      }

      setDialog({ kind: "none" });
    },
    [
      currentProjectId,
      dialog,
      deletePosition,
      deletePositions,
      deleteFolder,
      renamePosition,
      createFolder,
      clearSelection,
      positions,
    ]
  );

  const handleDialogCancel = useCallback(() => {
    setDialog({ kind: "none" });
  }, []);

  // ==========================================================================
  // Tree collapse toggle
  // ==========================================================================

  const handleToggleCollapse = useCallback((folderPath: string) => {
    setCollapsedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderPath)) {
        next.delete(folderPath);
      } else {
        next.add(folderPath);
      }
      return next;
    });
  }, []);

  // ==========================================================================
  // D. Drag & Drop (manual mouse events)
  // ==========================================================================

  // Mouse down on a position: store start coordinates
  const handlePositionMouseDown = useCallback(
    (e: ReactMouseEvent<HTMLButtonElement>, path: string) => {
      // Only primary button triggers drag
      if (e.button !== 0) return;
      // Don't start drag if modifier keys are held (they indicate selection intent)
      if (e.ctrlKey || e.metaKey || e.shiftKey) return;

      dragStartRef.current = { x: e.clientX, y: e.clientY, path };
    },
    []
  );

  useEffect(() => {
    const DRAG_THRESHOLD = 5; // px

    const onMouseMove = (e: MouseEvent) => {
      if (!dragStartRef.current) return;

      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist >= DRAG_THRESHOLD) {
        // Activate drag mode
        const dragPath = dragStartRef.current.path;
        const pathsToDrag =
          selectedPaths.includes(dragPath) && selectedPaths.length > 1
            ? selectedPaths
            : [dragPath];

        setDragging(true, pathsToDrag);
        // Change cursor globally
        document.body.style.cursor = "grabbing";

        // Detect hover over folder drop targets
        const el = document.elementFromPoint(e.clientX, e.clientY);
        const folderEl = el?.closest("[data-folder-path]");
        const folderPath = folderEl?.getAttribute("data-folder-path") ?? null;
        setDragOverFolder(folderPath);
      } else if (isDragging) {
        // Already dragging – update hover target
        const el = document.elementFromPoint(e.clientX, e.clientY);
        const folderEl = el?.closest("[data-folder-path]");
        const folderPath = folderEl?.getAttribute("data-folder-path") ?? null;
        setDragOverFolder(folderPath);
      }
    };

    const onMouseUp = async (e: MouseEvent) => {
      if (!dragStartRef.current) return;

      if (isDragging && currentProjectId) {
        const { dragPaths } = useProjectStore.getState();

        // Determine drop target
        const el = document.elementFromPoint(e.clientX, e.clientY);
        const folderEl = el?.closest("[data-folder-path]");
        const rootDropEl = el?.closest("[data-root-drop]");

        let targetFolder: string | null = null;

        if (folderEl) {
          targetFolder = folderEl.getAttribute("data-folder-path") ?? null;
        } else if (rootDropEl) {
          targetFolder = "";
        }

        if (targetFolder !== null) {
          // Move all dragged positions to the target folder
          for (const dp of dragPaths) {
            const currentFolder = getDirectFolder(dp);
            // Skip if source folder equals target folder
            if (currentFolder !== targetFolder) {
              await movePosition(currentProjectId, dp, targetFolder);
            }
          }
        }
      }

      // Clean up drag state
      dragStartRef.current = null;
      setDragging(false);
      setDragOverFolder(null);
      document.body.style.cursor = "";
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);

    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, [isDragging, currentProjectId, selectedPaths, setDragging, movePosition]);

  // ==========================================================================
  // Dialog: rename – derive initial value from position
  // ==========================================================================

  const renameInitialValue =
    dialog.kind === "renamePosition" ? dialog.currentLabel : "";

  // ==========================================================================
  // Render
  // ==========================================================================

  const hasPositions = positions.length > 0;

  return (
    <div className="flex h-full flex-col">
      {/* ===================================================================
          Top: Project selector
          =================================================================== */}
      <div className="shrink-0 border-b border-[var(--border)] p-2">
        <p className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
          Projekt
        </p>

        {loadingProjects ? (
          <p className="px-1 text-xs text-[var(--muted-foreground)] italic">
            Lade Projekte&hellip;
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
                <option value="">&ndash; Projekt w&auml;hlen &ndash;</option>
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

      {/* ===================================================================
          Middle: Position tree (scrollable)
          =================================================================== */}
      <div className="flex-1 overflow-y-auto py-1">
        {/* Root-level drop zone indicator (shown during drag) */}
        {isDragging && (
          <div
            data-root-drop="true"
            className="mx-2 mb-1 rounded border border-dashed border-[var(--border)] px-2 py-1 text-[10px] text-[var(--muted-foreground)] text-center"
          >
            Hierher ziehen (Projektebene)
          </div>
        )}

        {!currentProjectId ? (
          <p className="px-3 py-2 text-xs text-[var(--muted-foreground)] italic">
            Kein Projekt gew&auml;hlt
          </p>
        ) : loadingPositions ? (
          <p className="px-3 py-2 text-xs text-[var(--muted-foreground)] italic">
            Lade Positionen&hellip;
          </p>
        ) : !hasPositions ? (
          <p className="px-3 py-2 text-xs text-[var(--muted-foreground)] italic">
            Keine Positionen vorhanden
          </p>
        ) : (
          <FolderGroup
            node={tree}
            depth={0}
            collapsedFolders={collapsedFolders}
            onToggleCollapse={handleToggleCollapse}
            activePositionPath={currentPositionPath}
            selectedPaths={selectedPaths}
            dragOverFolder={dragOverFolder}
            onPositionLoad={handleLoadPosition}
            onPositionMouseDown={handlePositionMouseDown}
            onPositionClick={handlePositionClick}
            onPositionContextMenu={handlePositionContextMenu}
            onFolderContextMenu={handleFolderContextMenu}
          />
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
                &#x2715;
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ===================================================================
          Bottom: Save bar
          =================================================================== */}
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
                  &#x25CF;
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
          {/* Save button removed – saving happens automatically (useAutoSave, 2s debounce) */}

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

      {/* ===================================================================
          Context Menu (portal, see ContextMenu.tsx)
          =================================================================== */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenuItems}
          onClose={closeContextMenu}
        />
      )}

      {/* ===================================================================
          Modal Dialogs
          =================================================================== */}

      {/* Confirm: delete single position */}
      <ConfirmDialog
        open={dialog.kind === "confirmDeletePosition"}
        title="Position löschen"
        message="Soll die Position wirklich gelöscht werden? Diese Aktion kann nicht rückgängig gemacht werden."
        danger
        onConfirm={() => handleDialogConfirm()}
        onCancel={handleDialogCancel}
      />

      {/* Confirm: delete multiple positions */}
      <ConfirmDialog
        open={dialog.kind === "confirmDeletePositions"}
        title="Positionen löschen"
        message={
          dialog.kind === "confirmDeletePositions"
            ? `Sollen ${dialog.paths.length} Positionen wirklich gelöscht werden? Diese Aktion kann nicht rückgängig gemacht werden.`
            : ""
        }
        danger
        onConfirm={() => handleDialogConfirm()}
        onCancel={handleDialogCancel}
      />

      {/* Confirm: delete folder */}
      <ConfirmDialog
        open={dialog.kind === "confirmDeleteFolder"}
        title="Ordner löschen"
        message="Soll der Ordner und alle darin enthaltenen Positionen wirklich gelöscht werden? Diese Aktion kann nicht rückgängig gemacht werden."
        danger
        onConfirm={() => handleDialogConfirm()}
        onCancel={handleDialogCancel}
      />

      {/* Input: rename position */}
      <InputDialog
        open={dialog.kind === "renamePosition"}
        title="Position umbenennen"
        label='Neuer Name (Format: "Nummer – Name")'
        initialValue={renameInitialValue}
        placeholder="z.B. 1.01 – HT 1 Wohnzimmer"
        confirmLabel="Umbenennen"
        onConfirm={(v) => handleDialogConfirm(v)}
        onCancel={handleDialogCancel}
      />

      {/* Input: new folder */}
      <InputDialog
        open={dialog.kind === "newFolder"}
        title="Neuer Ordner"
        label="Ordnername"
        placeholder="z.B. EG"
        confirmLabel="Erstellen"
        onConfirm={(v) => handleDialogConfirm(v)}
        onCancel={handleDialogCancel}
      />
    </div>
  );
}
