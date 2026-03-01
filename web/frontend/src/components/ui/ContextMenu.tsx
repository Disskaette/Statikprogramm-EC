/**
 * Reusable context menu component rendered into document.body via a React portal.
 *
 * Usage:
 *   const [menu, setMenu] = useState<{x:number; y:number} | null>(null);
 *
 *   <div onContextMenu={(e) => { e.preventDefault(); setMenu({x: e.clientX, y: e.clientY}); }}>
 *     ...
 *   </div>
 *
 *   {menu && (
 *     <ContextMenu
 *       x={menu.x} y={menu.y}
 *       items={[{ label: "Rename", onClick: handleRename }]}
 *       onClose={() => setMenu(null)}
 *     />
 *   )}
 */

import { useEffect, useRef } from "react";
import ReactDOM from "react-dom";

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface ContextMenuItem {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  /** Red text for destructive actions */
  danger?: boolean;
}

export interface ContextMenuSeparator {
  separator: true;
}

export type ContextMenuEntry = ContextMenuItem | ContextMenuSeparator;

interface ContextMenuProps {
  x: number;
  y: number;
  items: ContextMenuEntry[];
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MENU_WIDTH = 180;
const MENU_ITEM_HEIGHT = 28; // rough estimate per item for boundary detection
const SEPARATOR_HEIGHT = 9;
const PADDING = 8; // extra edge buffer in px

/** True if the entry is a separator */
function isSeparator(entry: ContextMenuEntry): entry is ContextMenuSeparator {
  return "separator" in entry && entry.separator === true;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // ---- Boundary-aware positioning ----------------------------------------
  // Estimate the menu height from the item list so we can flip/clamp before
  // the first paint. We can't measure the DOM node on the first render, so we
  // use the approximation and correct on mount if needed.
  const estimatedHeight =
    items.reduce((sum, entry) => {
      return sum + (isSeparator(entry) ? SEPARATOR_HEIGHT : MENU_ITEM_HEIGHT);
    }, 0) + PADDING * 2;

  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let left = x;
  let top = y;

  if (left + MENU_WIDTH + PADDING > vw) {
    left = Math.max(PADDING, vw - MENU_WIDTH - PADDING);
  }
  if (top + estimatedHeight + PADDING > vh) {
    top = Math.max(PADDING, vh - estimatedHeight - PADDING);
  }

  // ---- Correct position after actual layout on mount ---------------------
  useEffect(() => {
    const el = menuRef.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const vwNow = window.innerWidth;
    const vhNow = window.innerHeight;

    let adjustLeft = parseFloat(el.style.left);
    let adjustTop = parseFloat(el.style.top);

    if (adjustLeft + rect.width + PADDING > vwNow) {
      adjustLeft = Math.max(PADDING, vwNow - rect.width - PADDING);
    }
    if (adjustTop + rect.height + PADDING > vhNow) {
      adjustTop = Math.max(PADDING, vhNow - rect.height - PADDING);
    }

    el.style.left = `${adjustLeft}px`;
    el.style.top = `${adjustTop}px`;
  }, []);

  // ---- Dismiss handlers --------------------------------------------------
  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      // Close if the click is outside the menu element
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    const handleScroll = () => {
      onClose();
    };

    // Use capture phase for mousedown so it fires before any target handlers
    document.addEventListener("mousedown", handleMouseDown, true);
    document.addEventListener("keydown", handleKeyDown, true);
    document.addEventListener("scroll", handleScroll, true);

    return () => {
      document.removeEventListener("mousedown", handleMouseDown, true);
      document.removeEventListener("keydown", handleKeyDown, true);
      document.removeEventListener("scroll", handleScroll, true);
    };
  }, [onClose]);

  // ---- Render ------------------------------------------------------------
  const menu = (
    <div
      ref={menuRef}
      role="menu"
      style={{ position: "fixed", left, top }}
      className={[
        "bg-[var(--background)]",
        "border border-[var(--border)]",
        "shadow-lg",
        "rounded-md",
        "py-1",
        "min-w-[160px]",
        "z-50",
        // Ensure the menu sits above other stacking contexts
        "isolation-isolate",
      ].join(" ")}
      // Prevent the document mousedown listener from firing when clicking
      // inside the menu itself (children call onClose via their onClick)
      onMouseDown={(e) => e.stopPropagation()}
    >
      {items.map((entry, idx) => {
        if (isSeparator(entry)) {
          return (
            <div
              key={idx}
              role="separator"
              className="border-t border-[var(--border)] my-1"
            />
          );
        }

        const item = entry as ContextMenuItem;

        return (
          <button
            key={idx}
            role="menuitem"
            disabled={item.disabled}
            className={[
              "w-full text-left",
              "px-3 py-1.5",
              "text-xs",
              "transition-colors",
              item.disabled
                ? "opacity-50 cursor-not-allowed text-[var(--foreground)]"
                : item.danger
                  ? "text-red-500 hover:bg-[var(--muted)] cursor-pointer"
                  : "text-[var(--foreground)] hover:bg-[var(--muted)] cursor-pointer",
            ].join(" ")}
            onClick={() => {
              if (!item.disabled) {
                onClose();
                item.onClick();
              }
            }}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );

  return ReactDOM.createPortal(menu, document.body);
}
