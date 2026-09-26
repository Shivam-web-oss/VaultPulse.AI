'use client';

import type { ReactNode } from 'react';
import { AuthProvider } from '../../context/AuthContext';

export function AppProvider({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
