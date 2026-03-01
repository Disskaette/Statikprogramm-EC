import { useTheme } from "@/hooks/useTheme";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm
                 bg-[var(--secondary)] text-[var(--secondary-foreground)]
                 hover:bg-[var(--accent)] transition-colors cursor-pointer"
      title={theme === "dark" ? "Light Mode" : "Dark Mode"}
    >
      {theme === "dark" ? "\u2600\uFE0F Light" : "\uD83C\uDF19 Dark"}
    </button>
  );
}
