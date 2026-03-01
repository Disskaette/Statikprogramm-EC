/**
 * Modal confirmation dialog built on the native HTML <dialog> element.
 *
 * Usage:
 *   <ConfirmDialog
 *     open={showDialog}
 *     title="Position löschen"
 *     message="Soll die Position wirklich gelöscht werden? Diese Aktion kann nicht rückgängig gemacht werden."
 *     danger
 *     onConfirm={handleDelete}
 *     onCancel={() => setShowDialog(false)}
 *   />
 *
 * The dialog uses showModal() / close() so it:
 *   - sits in the top layer above all other content
 *   - traps focus correctly
 *   - closes on native Escape key
 */

import { useEffect, useRef } from "react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  /** Label for the confirm button. Defaults to "Löschen" */
  confirmLabel?: string;
  /** Label for the cancel button. Defaults to "Abbrechen" */
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  /** When true the confirm button is styled in red (destructive action) */
  danger?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Löschen",
  cancelLabel = "Abbrechen",
  onConfirm,
  onCancel,
  danger = false,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  // ---- Open / close via native API ---------------------------------------
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      if (!dialog.open) {
        dialog.showModal();
      }
    } else {
      if (dialog.open) {
        dialog.close();
      }
    }
  }, [open]);

  // ---- Intercept native "cancel" event (Escape key) ----------------------
  // The browser fires a "cancel" event on Escape before closing the dialog.
  // We preventDefault to keep control, then call onCancel ourselves.
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

  // ---- Render ------------------------------------------------------------
  return (
    <dialog
      ref={dialogRef}
      className={[
        // Reset browser dialog defaults
        "p-0 m-auto",
        "bg-transparent",
        // Backdrop colour (::backdrop pseudo-element via Tailwind isn't reliable; use inline style trick)
        "backdrop:bg-black/50 backdrop:backdrop-blur-sm",
      ].join(" ")}
      // Clicking the backdrop (the <dialog> element itself, outside the card)
      // triggers onCancel. The card stops propagation.
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
        // Prevent backdrop-click from propagating to the <dialog> element
        onClick={(e) => e.stopPropagation()}
      >
        {/* Title */}
        <h2 className="text-sm font-semibold text-[var(--foreground)] leading-snug">
          {title}
        </h2>

        {/* Message */}
        <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">
          {message}
        </p>

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
            onClick={onConfirm}
            className={[
              "px-3 py-1.5 text-xs rounded font-medium",
              "transition-colors cursor-pointer",
              danger
                ? "bg-red-500 hover:bg-red-600 text-white border border-red-500"
                : "bg-[var(--primary)] hover:opacity-90 text-[var(--primary-foreground)] border border-[var(--primary)]",
            ].join(" ")}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
