'use client';

import type { ReactNode } from 'react';
import { ThemeToggle } from '../ui/ThemeToggle';

export function AuthPageFrame({ children }: { children: ReactNode }) {
  return (
    <main className="auth-page relative flex min-h-screen items-center justify-center px-4">
      <ThemeToggle className="auth-theme-toggle absolute right-5 top-5" />
      <div className="auth-card w-full max-w-md rounded-2xl border p-6 shadow-[0_0_40px_rgba(184,233,120,0.1)]">
        {children}
      </div>
    </main>
  );
}