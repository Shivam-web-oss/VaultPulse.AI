'use client';

import { createContext, useContext, useSyncExternalStore, type ReactNode } from 'react';
import type { AuthResponse } from '../lib/authApi';
import { clearAuth, readStoredSession, storeAuth, type AuthUser } from '../types/user';

const AUTH_CHANGE_EVENT = 'vaultpulse-auth-change';

type AuthContextValue = {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  setSession: (response: AuthResponse) => void;
  logOut: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function subscribe(callback: () => void) {
  window.addEventListener('storage', callback);
  window.addEventListener(AUTH_CHANGE_EVENT, callback);
  return () => {
    window.removeEventListener('storage', callback);
    window.removeEventListener(AUTH_CHANGE_EVENT, callback);
  };
}

function getSnapshot() {
  return `${localStorage.getItem('vaultpulse_auth') ?? ''}:${localStorage.getItem('vaultpulse_access_token') ?? ''}`;
}

function getServerSnapshot() {
  return '';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const authSnapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const session = authSnapshot ? readStoredSession() : null;

  const setSession = (response: AuthResponse) => {
    storeAuth(response.user, response.access_token);
    window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
  };

  const logOut = () => {
    clearAuth();
    window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
  };

  return <AuthContext.Provider value={{ user: session?.user ?? null, accessToken: session?.accessToken ?? null, isAuthenticated: Boolean(session), setSession, logOut }}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuthContext must be used inside AuthProvider');
  return context;
}
