'use client';

import type { ReactNode } from 'react';
import { AuthProvider } from '../../context/AuthContext';
import { ThemeProvider } from '../../context/ThemeContext';

export function AppProvider({ children }: { children: ReactNode }) {
  return <ThemeProvider><AuthProvider>{children}</AuthProvider></ThemeProvider>;
}
