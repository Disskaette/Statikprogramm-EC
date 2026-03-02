/**
 * Augments the built-in FileSystemHandle types with permission methods
 * and async iteration that are part of the File System Access API but
 * not yet fully covered in lib.dom.d.ts for this TypeScript version.
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

/**
 * Augment FileSystemDirectoryHandle with async iteration methods.
 * The DOM lib types FileSystemDirectoryHandle as iterable via Symbol.asyncIterator
 * only when DOM.Iterable is included – but entries() / keys() / values() returning
 * AsyncIterableIterator are missing from the shipped .d.ts in TS 5.x.
 *
 * Spec: https://wicg.github.io/file-system-access/#dom-filesystemdirectoryhandle-entries
 */
interface FileSystemDirectoryHandle {
  entries(): AsyncIterableIterator<[string, FileSystemHandle]>;
  keys(): AsyncIterableIterator<string>;
  values(): AsyncIterableIterator<FileSystemHandle>;
  [Symbol.asyncIterator](): AsyncIterableIterator<[string, FileSystemHandle]>;
}

interface DirectoryPickerOptions {
  mode?: "read" | "readwrite";
  startIn?: FileSystemHandle | "desktop" | "documents" | "downloads" | "music" | "pictures" | "videos";
  id?: string;
}

interface Window {
  showDirectoryPicker(options?: DirectoryPickerOptions): Promise<FileSystemDirectoryHandle>;
}
