import { clearAuth, readStoredSession } from '../types/user';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const session = readStoredSession();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (session?.accessToken) headers.set('Authorization', `Bearer ${session.accessToken}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (response.status === 401) {
    clearAuth();
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('vaultpulse-auth-change'));
  }
  if (!response.ok) throw new Error((await response.text()) || 'Request failed');
  return response.json() as Promise<T>;
}
