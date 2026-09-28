'use client';

import { createContext, startTransition, useContext, useEffect, useState, type ReactNode } from 'react';

export type Theme = 'light' | 'dark';

type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);
const THEME_STORAGE_KEY = 'vaultpulse_theme';
const LEGACY_THEME_STORAGE_KEY = 'vaultpulse_auth_theme';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light');

  useEffect(() => {
    let savedTheme = localStorage.getItem(THEME_STORAGE_KEY) ?? localStorage.getItem(LEGACY_THEME_STORAGE_KEY);
    if (!savedTheme) {
      try {
        const savedAppearance = JSON.parse(localStorage.getItem('ai-assistant-settings') ?? '{}').appearance;
        if (savedAppearance === 'dark' || savedAppearance === 'light') savedTheme = savedAppearance;
      } catch {
        savedTheme = null;
      }
    }
    if (savedTheme === 'dark' || savedTheme === 'light') {
      startTransition(() => setTheme(savedTheme));
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = nextTheme;
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    setTheme(nextTheme);
  };

  return <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used inside ThemeProvider');
  return context;
}