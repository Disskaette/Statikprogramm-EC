/**
 * TypeScript interfaces for local (File System Access API) projects.
 *
 * A LocalProject mirrors the server Project shape, but uses a
 * FileSystemDirectoryHandle instead of a server UUID.
 */

import type { Position } from "@/types/project";

// ---------------------------------------------------------------------------
// Handle storage entry (persisted in IndexedDB)
// ---------------------------------------------------------------------------

/** Key used in IndexedDB to store a directory handle */
export type HandleKey = string; // e.g. "local:Demo_Wohnhaus"

// ---------------------------------------------------------------------------
// Local project metadata (read from project.json in the opened folder)
// ---------------------------------------------------------------------------

export interface LocalProjectMeta {
  /** UUID from project.json (same as server format) */
  uuid: string;
  /** Human-readable project name */
  name: string;
  /** ISO 8601 creation timestamp */
  created: string;
  /** ISO 8601 last-modified timestamp */
  last_modified: string;
  /** Optional description */
  description: string;
}

// ---------------------------------------------------------------------------
// Full local project entry (in useLocalProjectStore)
// ---------------------------------------------------------------------------

export interface LocalProjectEntry {
  /**
   * Stable key for IndexedDB and store lookup.
   * Format: "local:<folder-name>" e.g. "local:Demo_Wohnhaus"
   */
  key: HandleKey;
  /** The directory handle – used for all file I/O */
  handle: FileSystemDirectoryHandle;
  /** Metadata parsed from project.json */
  meta: LocalProjectMeta;
  /**
   * Flat list of all positions found by scanning the folder recursively.
   * Same Position shape as server, but file_path is relative to handle root.
   */
  positions: Position[];
  /** True if the handle currently has readwrite permission */
  hasPermission: boolean;
}

// ---------------------------------------------------------------------------
// Permission status
// ---------------------------------------------------------------------------

export type PermissionStatus = "granted" | "prompt" | "denied";
