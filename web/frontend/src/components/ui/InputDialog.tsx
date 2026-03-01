/**
 * Modal input dialog built on the native HTML <dialog> element.
 *
 * Presents a single text input (auto-focused on open) with OK / Cancel
 * buttons. The confirm button is disabled while the input is empty.
 * Submit with Enter, cancel with Escape.
 *
 * Usage:
 *   <InputDialog
 *     open={showRename}
 *     title="Position umbenennen"
 *     label="Neuer Name"
 *     initialValue={currentName}
 *     placeholder="z. B. HT 1 – Wohnzimmer"
 *     confirmLabel="Umbenennen"
 *     onConfirm={(value) => handleRename(value)}
 *     onCancel={() => setShowRename(false)}
 *   />
 */

import { useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface InputDialogProps {
  open: boolean;
  title: string;
  label: string;
  initialValue?: string;
  placeholder?: string;
  /** Label for the confirm button. Defaults to "OK" */
  confirmLabel?: string;
  /** Label for the cancel button. Defaults to "Abbrechen" */
  cancelLabel?: string;
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function InputDialog({
  open,
  title,
  label,
  initialValue = "",
  placeholder,
  confirmLabel = "OK",
  cancelLabel = "Abbrechen",
  onConfirm,
  onCancel,
}: InputDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Internal state – reset from initialValue whenever the dialog is opened
  const [value, setValue] = useState(initialValue);

  // ---- Sync value when dialog opens (initialValue may change) ------------
  useEffect(() => {
    if (open) {
      setValue(initialValue);
    }
  }, [open, initialValue]);

  // ---- Open / close via native API ---------------------------------------
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      if (!dialog.open) {
        dialog.showModal();
      }
      // Auto-focus the input after the dialog transitions in
      requestAnimationFrame(() => {
        const input = inputRef.current;
        if (input) {
          input.focus();
          input.select();
        }
      });
    } else {
      if (dialog.open) {
        dialog.close();
      }
    }
  }, [open]);

  // ---- Intercept native "cancel" event (Escape key) ----------------------
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      e.preventDefault();
      onCancel();
    };

    dialog.addEventListener("cancel", handleCancel);
    return () => dialog.removeEventListener("cancel", handleCancel);
  }, [onCancel]);

  // ---- Handlers ----------------------------------------------------------
  const handleConfirm = () => {
    const trimmed = value.trim();
    if (trimmed.length === 0) return;
    onConfirm(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleConfirm();
    }
    // Escape is handled natively by <dialog> + the cancel event listener above
  };

  const isEmpty = value.trim().length === 0;

  // ---- Render ------------------------------------------------------------
  return (
    <dialog
      ref={dialogRef}
      className={[
        "p-0 m-auto",
        "bg-transparent",
        "backdrop:bg-black/50 backdrop:backdrop-blur-sm",
      ].join(" ")}
      onClick={onCancel}
    >
      {/* Card */}
      <div
        role="document"
        className={[
          "bg-[var(--background)]",
          "rounded-lg",
          "border border-[var(--border)]",
          "shadow-xl",
          "p-6",
          "max-w-sm w-full",
          "flex flex-col gap-4",
        ].join(" ")}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Title */}
        <h2 className="text-sm font-semibold text-[var(--foreground)] leading-snug">
          {title}
        </h2>

        {/* Input field */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="input-dialog-field"
            className="text-xs text-[var(--muted-foreground)]"
          >
            {label}
          </label>
          <input
            ref={inputRef}
            id="input-dialog-field"
            type="text"
            value={value}
            placeholder={placeholder}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className={[
              "w-full px-2.5 py-1.5",
              "text-xs",
              "rounded",
              "border border-[var(--input)]",
              "bg-[var(--background)] text-[var(--foreground)]",
              "placeholder:text-[var(--muted-foreground)]",
              "outline-none",
              "focus:ring-2 focus:ring-[var(--ring)] focus:ring-offset-1 focus:ring-offset-[var(--background)]",
              "transition-shadow",
            ].join(" ")}
          />
        </div>

        {/* Buttons */}
        <div className="flex justify-end gap-2 pt-1">
          {/* Cancel */}
          <button
            type="button"
            onClick={onCancel}
            className={[
              "px-3 py-1.5 text-xs rounded",
              "border border-[var(--border)]",
              "bg-[var(--background)] text-[var(--foreground)]",
              "hover:bg-[var(--muted)]",
              "transition-colors cursor-pointer",
            ].join(" ")}
          >
            {cancelLabel}
          </button>

          {/* Confirm */}
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isEmpty}
            className={[
              "px-3 py-1.5 text-xs rounded font-medium",
              "bg-[var(--primary)] text-[var(--primary-foreground)]",
              "border border-[var(--primary)]",
              "transition-colors",
              isEmpty
                ? "opacity-40 cursor-not-allowed"
                : "hover:opacity-90 cursor-pointer",
            ].join(" ")}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
