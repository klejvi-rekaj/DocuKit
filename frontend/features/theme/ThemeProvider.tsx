"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type ThemePreference = "system" | "light" | "dark";
export type AppliedTheme = "light" | "dark";

interface ThemeContextValue {
  theme: ThemePreference;
  appliedTheme: AppliedTheme;
  setTheme: (theme: ThemePreference) => void;
}

const THEME_STORAGE_KEY = "dokukit-theme";
const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemTheme(): AppliedTheme {
  if (typeof window === "undefined") {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyThemeToDocument(theme: ThemePreference, appliedTheme: AppliedTheme) {
  document.documentElement.dataset.themeChoice = theme;
  document.documentElement.dataset.theme = appliedTheme;
  document.documentElement.style.colorScheme = appliedTheme;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemePreference>(() => {
    if (typeof document !== "undefined") {
      const existing = document.documentElement.dataset.themeChoice;
      if (existing === "light" || existing === "dark" || existing === "system") {
        return existing;
      }
    }

    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === "light" || stored === "dark" || stored === "system") {
        return stored;
      }
    }

    return "system";
  });
  const [systemTheme, setSystemTheme] = useState<AppliedTheme>(() => {
    if (typeof document !== "undefined") {
      const existing = document.documentElement.dataset.theme;
      if (existing === "light" || existing === "dark") {
        return existing;
      }
    }
    return getSystemTheme();
  });

  const appliedTheme = useMemo<AppliedTheme>(() => {
    return theme === "system" ? systemTheme : theme;
  }, [systemTheme, theme]);

  useEffect(() => {
    applyThemeToDocument(theme, appliedTheme);
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [appliedTheme, theme]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const updateSystemTheme = () => {
      setSystemTheme(mediaQuery.matches ? "dark" : "light");
    };

    updateSystemTheme();
    mediaQuery.addEventListener("change", updateSystemTheme);
    return () => mediaQuery.removeEventListener("change", updateSystemTheme);
  }, []);

  const value = useMemo(
    () => ({
      theme,
      appliedTheme,
      setTheme: setThemeState,
    }),
    [appliedTheme, theme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider.");
  }
  return context;
}
