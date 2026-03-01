import { type ReactNode } from "react";
import { ThemeToggle } from "./ThemeToggle";

interface LayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export function Layout({ sidebar, children }: LayoutProps) {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Top bar */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--background)] px-4">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold">Statik-Tool</span>
          <span className="text-xs text-[var(--muted-foreground)]">v2.0 Web</span>
        </div>
        <ThemeToggle />
      </header>

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 shrink-0 overflow-y-auto border-r border-[var(--border)] bg-[var(--muted)]/30">
          {sidebar}
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
