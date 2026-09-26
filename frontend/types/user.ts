export type AuthUser = {
  id: string;
  email: string;
  name: string;
};

export type AuthSession = {
  user: AuthUser;
  accessToken: string;
};

export type LoginForm = {
  email: string;
  password: string;
};

export type RegistrationForm = LoginForm & {
  name: string;
  confirmPassword: string;
};

export const AUTH_STORAGE_KEY = 'vaultpulse_auth';
export const AUTH_TOKEN_STORAGE_KEY = 'vaultpulse_access_token';

export function readStoredSession(): AuthSession | null {
  if (typeof window === 'undefined') return null;

  try {
    const rawUser = localStorage.getItem(AUTH_STORAGE_KEY);
    const accessToken = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    return rawUser && accessToken ? { user: JSON.parse(rawUser) as AuthUser, accessToken } : null;
  } catch {
    return null;
  }
}

export function readStoredAuth() {
  return readStoredSession()?.user ?? null;
}

export function storeAuth(user: AuthUser, accessToken: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, accessToken);
  }
}

export function clearAuth() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }
}

export function isAuthenticated() {
  return Boolean(readStoredAuth());
}
