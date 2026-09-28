'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

export function ThemeToggle({ className = '' }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const nextTheme = theme === 'light' ? 'dark' : 'light';
  const Icon = theme === 'light' ? Moon : Sun;

  return (
    <button
      type="button"
      onClick={toggleTheme}
      title={`Switch to ${nextTheme} mode`}
      aria-label={`Switch to ${nextTheme} mode`}
      className={`theme-toggle inline-flex h-10 w-10 items-center justify-center rounded-full border ${className}`}
    >
      <Icon size={17} aria-hidden="true" />
    </button>
  );
}