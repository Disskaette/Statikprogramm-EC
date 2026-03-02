/**
 * Augments the built-in FileSystemHandle types with permission methods
 * that are part of the File System Access API but not yet in lib.dom.d.ts
 * for this TypeScript version.
 *
 * Spec: https://wicg.github.io/file-system-access/#api-filesystemhandle
 */

interface FileSystemPermissionDescriptor {
  mode?: "read" | "readwrite";
}

interface FileSystemHandle {
  queryPermission(descriptor?: FileSystemPermissionDescriptor): Promise<PermissionState>;
  requestPermission(descriptor?: FileSystemPermissionDescriptor): Promise<PermissionState>;
}
