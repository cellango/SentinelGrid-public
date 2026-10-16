'use client';

import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import themeConfig from '../../../theme.config.json';

type ThemeChoice = 'light' | 'dark' | 'system';

type ThemeContextType = {
  theme: ThemeChoice;
  setTheme: (theme: ThemeChoice) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_STORAGE_KEY = 'sentinelgrid_theme';
const DEFAULT_THEME: ThemeChoice =
  (themeConfig as any)?.defaultTheme === 'light'
    ? 'light'
    : (themeConfig as any)?.defaultTheme === 'system'
    ? 'system'
    : 'dark';

function getPreferred(theme: ThemeChoice): 'light' | 'dark' {
  if (theme === 'system' && typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return theme === 'dark' ? 'dark' : 'light';
}

function applyTheme(theme: ThemeChoice) {
  const resolved = getPreferred(theme);
  const targets = [document.documentElement, document.body].filter(Boolean) as HTMLElement[];
  targets.forEach((el) => {
    if (resolved === 'dark') {
      el.classList.add('dark');
    } else {
      el.classList.remove('dark');
    }
    el.setAttribute('data-theme', resolved);
  });
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeChoice>(DEFAULT_THEME);

  // On mount, load from storage or use config default
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = localStorage.getItem(THEME_STORAGE_KEY) as ThemeChoice | null;
    const next = stored || DEFAULT_THEME;
    setThemeState(next);
    applyTheme(next);

    if (next === 'system') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      const handler = () => applyTheme('system');
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }
  }, []);

  const setTheme = (choice: ThemeChoice) => {
    setThemeState(choice);
    if (typeof window !== 'undefined') {
      localStorage.setItem(THEME_STORAGE_KEY, choice);
      applyTheme(choice);
    }
  };

  const toggleTheme = () => {
    const next: ThemeChoice = theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark';
    setTheme(next);
  };

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      toggleTheme,
    }),
    [theme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
