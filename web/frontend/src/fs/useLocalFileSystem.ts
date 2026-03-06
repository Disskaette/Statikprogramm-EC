/**
 * useLocalFileSystem – File System Access API wrapper.
 *
 * All functions are async and throw descriptive errors on failure.
 * Feature detection: check isFileSystemAccessSupported() before calling
 * any picker functions.
 */

import type { LocalProjectMeta } from "@/types/localProject";
import type { Position } from "@/types/project";

// ---------------------------------------------------------------------------
// Feature detection
// ---------------------------------------------------------------------------

/** True if the browser supports the File System Access API (showDirectoryPicker) */
export function isFileSystemAccessSupported(): boolean {
  return "showDirectoryPicker" in window;
}

// ---------------------------------------------------------------------------
// Open folder picker
// ---------------------------------------------------------------------------

/**
 * Opens the browser's directory picker and returns the chosen handle.
 * Throws AbortError if the user cancels.
 */
export async function pickDirectory(): Promise<FileSystemDirectoryHandle> {
  if (!isFileSystemAccessSupported()) {
    throw new Error(
      "Lokale Projekte werden in Chrome, Edge und Firefox 111+ unterstützt."
    );
  }
  return window.showDirectoryPicker({ mode: "readwrite" });
}

// ---------------------------------------------------------------------------
// Scan folder recursively
// ---------------------------------------------------------------------------

/**
 * Scans a directory handle recursively and collects all position JSON files.
 * Returns { meta, positions } where meta is from project.json and positions
 * is the flat list of all found positions with relative_path populated.
 */
export async function scanProjectFolder(
  handle: FileSystemDirectoryHandle
): Promise<{ meta: LocalProjectMeta; positions: Position[] }> {
  const meta = await readProjectJson(handle);
  const positions: Position[] = [];
  await collectPositions(handle, "", positions);
  return { meta, positions };
}

/** Read and parse project.json from the root of a handle */
async function readProjectJson(
  handle: FileSystemDirectoryHandle
): Promise<LocalProjectMeta> {
  try {
    const fileHandle = await handle.getFileHandle("project.json");
    const file = await fileHandle.getFile();
    const text = await file.text();
    const data = JSON.parse(text) as Record<string, unknown>;
    return {
      uuid: (data.uuid as string) || crypto.randomUUID(),
      name: (data.name as string) ?? handle.name,
      created: (data.created as string) ?? new Date().toISOString(),
      last_modified: (data.last_modified as string) ?? new Date().toISOString(),
      description: (data.description as string) ?? "",
    };
  } catch {
    // No project.json → generate stable metadata and persist it so future
    // calls always return the same UUID (avoids duplicate entries on re-scan).
    const meta = {
      uuid: crypto.randomUUID(),
      name: handle.name,
      created: new Date().toISOString(),
      last_modified: new Date().toISOString(),
      description: "",
    };
    try {
      const projectFile = await handle.getFileHandle("project.json", { create: true });
      const writable = await projectFile.createWritable();
      await writable.write(JSON.stringify(meta, null, 2));
      await writable.close();
    } catch {
      // Silently ignore if we can't write (e.g. read-only volume)
    }
    return meta;
  }
}

/**
 * Recursively walk a directory handle and push position entries.
 * prefix is the relative path from the project root (empty for root).
 */
async function collectPositions(
  dirHandle: FileSystemDirectoryHandle,
  prefix: string,
  out: Position[]
): Promise<void> {
  for await (const [name, entry] of dirHandle.entries()) {
    if (name === "project.json" || name.startsWith(".")) continue;

    if (entry.kind === "file" && name.endsWith(".json")) {
      const relativePath = prefix ? `${prefix}/${name}` : name;
      try {
        const file = await (entry as FileSystemFileHandle).getFile();
        const text = await file.text();
        const data = JSON.parse(text) as Record<string, unknown>;

        // Only include if it looks like a position (has position_nummer)
        if (data.position_nummer !== undefined) {
          out.push({
            position_nummer: (data.position_nummer as string) ?? "",
            position_name: (data.position_name as string) ?? "",
            created: (data.created as string) ?? "",
            last_modified: (data.last_modified as string) ?? "",
            active_module: (data.active_module as string) ?? "durchlauftraeger",
            modules: (data.modules as Record<string, unknown>) ?? {},
            file_path: relativePath,
            relative_path: relativePath,
          });
        }
      } catch {
        // Skip unreadable / malformed files silently
      }
    } else if (entry.kind === "directory") {
      const subPrefix = prefix ? `${prefix}/${name}` : name;
      await collectPositions(entry as FileSystemDirectoryHandle, subPrefix, out);
    }
  }
}

// ---------------------------------------------------------------------------
// Read a single position file
// ---------------------------------------------------------------------------

/**
 * Read a position JSON from a local folder by its relative_path.
 */
export async function readPositionFile(
  rootHandle: FileSystemDirectoryHandle,
  relativePath: string
): Promise<Position> {
  const fileHandle = await resolveFileHandle(rootHandle, relativePath);
  const file = await fileHandle.getFile();
  const text = await file.text();
  const data = JSON.parse(text) as Record<string, unknown>;
  return {
    position_nummer: (data.position_nummer as string) ?? "",
    position_name: (data.position_name as string) ?? "",
    created: (data.created as string) ?? "",
    last_modified: (data.last_modified as string) ?? "",
    active_module: (data.active_module as string) ?? "durchlauftraeger",
    modules: (data.modules as Record<string, unknown>) ?? {},
    file_path: relativePath,
    relative_path: relativePath,
  };
}

// ---------------------------------------------------------------------------
// Write a position file
// ---------------------------------------------------------------------------

/**
 * Write a position JSON to a local folder.
 * Creates parent directories if they do not exist.
 */
export async function writePositionFile(
  rootHandle: FileSystemDirectoryHandle,
  relativePath: string,
  data: Record<string, unknown>
): Promise<void> {
  const parts = relativePath.split("/");
  const fileName = parts.pop()!;
  let dirHandle: FileSystemDirectoryHandle = rootHandle;
  for (const part of parts) {
    dirHandle = await dirHandle.getDirectoryHandle(part, { create: true });
  }
  const fileHandle = await dirHandle.getFileHandle(fileName, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(
    JSON.stringify({ ...data, last_modified: new Date().toISOString() }, null, 2)
  );
  await writable.close();
}

// ---------------------------------------------------------------------------
// Delete a position file
// ---------------------------------------------------------------------------

/**
 * Delete a file from a local folder by relative path.
 */
export async function deletePositionFile(
  rootHandle: FileSystemDirectoryHandle,
  relativePath: string
): Promise<void> {
  const parts = relativePath.split("/");
  const fileName = parts.pop()!;
  let dirHandle: FileSystemDirectoryHandle = rootHandle;
  for (const part of parts) {
    dirHandle = await dirHandle.getDirectoryHandle(part);
  }
  await dirHandle.removeEntry(fileName);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Resolve a relative path like "EG/Position_1_01.json" to a FileSystemFileHandle */
async function resolveFileHandle(
  rootHandle: FileSystemDirectoryHandle,
  relativePath: string
): Promise<FileSystemFileHandle> {
  const parts = relativePath.split("/");
  const fileName = parts.pop()!;
  let dirHandle: FileSystemDirectoryHandle = rootHandle;
  for (const part of parts) {
    dirHandle = await dirHandle.getDirectoryHandle(part);
  }
  return dirHandle.getFileHandle(fileName);
}
