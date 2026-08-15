"use client";

// Light/dark switch. The actual class on <html> is set before hydration by
// the inline script in app/layout.tsx; this button only flips it and stores
// the choice. State syncs from the DOM inside a microtask (.then) to satisfy
// the react-hooks/set-state-in-effect rule (see PROGRESS.md).

import { useEffect, useState } from "react";
import uz from "@/i18n/uz.json";

export const THEME_KEY = "uniagent_theme";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    Promise.resolve().then(() => {
      setDark(document.documentElement.classList.contains("dark"));
    });
  }, []);

  const toggle = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem(THEME_KEY, next ? "dark" : "light");
    setDark(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      title={dark ? uz.common.themeLight : uz.common.themeDark}
      aria-label={dark ? uz.common.themeLight : uz.common.themeDark}
      className="flex h-9 w-9 items-center justify-center rounded-lg border border-line text-ink-soft transition-colors hover:bg-raised"
    >
      {dark ? (
        /* sun */
        <svg
          className="h-4.5 w-4.5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        /* moon */
        <svg
          className="h-4.5 w-4.5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  );
}
