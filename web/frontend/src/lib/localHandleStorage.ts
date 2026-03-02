/**
 * localHandleStorage – persists FileSystemDirectoryHandle in IndexedDB.
 *
 * Uses idb-keyval with a dedicated store ("statik-local" / "handles") so we
 * don't pollute the default store.
 *
 * Note: FileSystemDirectoryHandle is structured-cloneable → can be stored
 * in IndexedDB natively (no serialisation needed).
 */

import { createStore, get, set, del, keys } from "idb-keyval";
import type { HandleKey } from "@/types/localProject";

// Dedicated IndexedDB store (db: "statik-local", store: "handles")
const idbStore = createStore("statik-local", "handles");

/** Persist a handle under the given key */
export async function saveHandle(
  key: HandleKey,
  handle: FileSystemDirectoryHandle
): Promise<void> {
  await set(key, handle, idbStore);
}

/** Retrieve a previously saved handle, or null if not found */
export async function loadHandle(
  key: HandleKey
): Promise<FileSystemDirectoryHandle | null> {
  return (await get<FileSystemDirectoryHandle>(key, idbStore)) ?? null;
}

/** Remove a handle from IndexedDB */
export async function removeHandle(key: HandleKey): Promise<void> {
  await del(key, idbStore);
}

/** List all stored handle keys */
export async function listHandleKeys(): Promise<HandleKey[]> {
  return (await keys(idbStore)) as HandleKey[];
}

/**
 * Check the current permission state for a handle.
 * Returns 'granted', 'prompt', or 'denied'.
 */
export async function queryHandlePermission(
  handle: FileSystemDirectoryHandle
): Promise<PermissionState> {
  return handle.queryPermission({ mode: "readwrite" });
}

/**
 * Request readwrite permission for a handle.
 * Must be called from a user gesture (e.g. button click).
 * Returns the new permission state.
 */
export async function requestHandlePermission(
  handle: FileSystemDirectoryHandle
): Promise<PermissionState> {
  return handle.requestPermission({ mode: "readwrite" });
}
